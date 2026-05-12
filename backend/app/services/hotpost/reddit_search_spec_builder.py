from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from app.schemas.hotpost_signal import SourceScopeId
from app.schemas.hotpost_source_scopes import RedditSearchSpec, TimeFilter, TopicPack
from app.services.hotpost.growth_pack_intake import uses_growth_pack_intake_path
from app.services.hotpost.hotpost_supply_contract import get_supply_experimental_collect_rules, get_supply_scope
from app.services.hotpost.hotpost_supply_projection import get_topic_pack_payload
from app.services.hotpost.reddit_search_spec_allocator import allocate_listing_inputs, allocate_search_inputs
from app.services.hotpost.source_scope_catalog import get_scope_topic_packs, get_topic_pack_keyword_buckets


def build_reddit_search_specs(scope_id: SourceScopeId, *, include_experimental: bool = False) -> list[RedditSearchSpec]:
    specs: list[RedditSearchSpec] = []
    packs = _ordered_topic_packs(scope_id)
    for pack in packs:
        payload = get_topic_pack_payload(scope_id, pack.topic_pack_id)
        if uses_growth_pack_intake_path(scope_id, pack.topic_pack_id):
            specs.extend(
                    _build_listing_specs(
                        scope_id,
                        pack.topic_pack_id,
                        list(payload.get("listing_bridge_communities") or pack.subreddits),
                    dict(payload) | {
                        "listing_rules": list(payload.get("listing_bridge_rules") or payload["listing_rules"]),
                    },
                )
            )
            continue
        segments = list(payload.get("cluster_segments") or [])
        if not segments:
            keyword_buckets = get_topic_pack_keyword_buckets(scope_id, pack.topic_pack_id)
            segments = [
                {
                    "subreddits": pack.subreddits,
                    "keywords": keyword_buckets,
                    "source_mode": payload["source_mode"],
                    "listing_rules": payload["listing_rules"],
                    "search_templates": payload.get("search_templates") or [],
                }
            ]
        for segment in segments:
            search_specs = _build_search_specs(
                scope_id,
                pack.topic_pack_id,
                list(segment.get("search_subreddits") or segment["subreddits"]),
                dict(segment["keywords"]),
                dict(payload)
                | {
                    "topic_cluster_id": segment.get("cluster_id"),
                    "topic_cluster_ids": [segment["cluster_id"]] if segment.get("cluster_id") else [],
                    "bucket_priority": list(segment.get("bucket_priority") or payload["bucket_priority"]),
                    "search_templates": list(segment.get("search_templates") or []),
                    "search_subreddit_limit": segment.get("search_subreddit_limit", payload.get("search_subreddit_limit")),
                    "keywords_per_bucket": segment.get("keywords_per_bucket", payload.get("keywords_per_bucket")),
                    "template_queries_per_segment": segment.get("template_queries_per_segment", payload.get("template_queries_per_segment")),
                    "max_search_specs_per_segment": segment.get("max_search_specs_per_segment", payload.get("max_search_specs_per_segment")),
                },
            )
            listing_specs = _build_listing_specs(
                scope_id,
                pack.topic_pack_id,
                list(segment.get("listing_subreddits") or segment["subreddits"]),
                dict(payload)
                | {
                    "topic_cluster_id": segment.get("cluster_id"),
                    "topic_cluster_ids": [segment["cluster_id"]] if segment.get("cluster_id") else [],
                    "listing_rules": list(segment["listing_rules"]),
                    "listing_subreddit_limit": segment.get("listing_subreddit_limit", payload.get("listing_subreddit_limit")),
                    "max_listing_specs_per_segment": segment.get("max_listing_specs_per_segment", payload.get("max_listing_specs_per_segment")),
                },
            )
            source_mode = segment["source_mode"]
            if not segment.get("allow_listing", payload.get("allow_listing", True)):
                listing_specs = []
            if source_mode == "search-first":
                specs.extend(search_specs)
                specs.extend(listing_specs)
                continue
            specs.extend(listing_specs)
            specs.extend(search_specs)
    if include_experimental:
        specs.extend(_build_experimental_specs(scope_id))
    return specs


def _build_experimental_specs(scope_id: SourceScopeId) -> list[RedditSearchSpec]:
    rules = get_supply_experimental_collect_rules()
    if bool(rules.get("include_by_default")):
        raise ValueError("experimental_collect.include_by_default must stay false")
    scope = get_supply_scope(scope_id)
    clusters = dict(scope.get("topic_clusters") or {})
    topic_packs = dict(scope.get("topic_packs") or {})
    max_scope_communities = int(rules["max_communities_per_scope"])
    used_communities: set[str] = set()
    specs: list[RedditSearchSpec] = []

    for pack_id, pack in topic_packs.items():
        payload = get_topic_pack_payload(scope_id, str(pack_id))
        for cluster_id in list(pack.get("topic_clusters") or []):
            cluster = dict(clusters.get(str(cluster_id)) or {})
            experimental = _select_experimental_communities(
                cluster,
                used_communities=used_communities,
                max_scope_communities=max_scope_communities,
            )
            if not experimental:
                continue
            keywords = dict(payload.get("keywords") or {})
            segment_keywords = (
                dict(cluster.get("experimental_keyword_buckets") or {})
                or dict(cluster.get("keyword_buckets") or {})
                or keywords
            )
            if str(cluster.get("source_mode") or payload.get("source_mode")) == "listing-first":
                specs.extend(
                    _build_listing_specs(
                        scope_id,
                        str(pack_id),
                        experimental,
                        dict(payload)
                        | {
                            "topic_cluster_id": str(cluster_id),
                            "topic_cluster_ids": [str(cluster_id)],
                            "listing_rules": list(cluster.get("listing_rules") or payload["listing_rules"]),
                            "listing_subreddit_limit": rules["listing_subreddit_limit"],
                            "max_listing_specs_per_segment": rules["max_listing_specs_per_cluster"],
                        },
                        is_experimental_probe=True,
                        reason_prefix="experimental",
                    )
                )
            specs.extend(
                _build_search_specs(
                    scope_id,
                    str(pack_id),
                    experimental,
                    segment_keywords,
                    dict(payload)
                    | {
                        "topic_cluster_id": str(cluster_id),
                        "topic_cluster_ids": [str(cluster_id)],
                        "bucket_priority": list(cluster.get("bucket_priority") or payload["bucket_priority"]),
                        "search_templates": list(payload.get("search_templates") or []),
                        "search_subreddit_limit": rules["search_subreddit_limit"],
                        "keywords_per_bucket": 1,
                        "template_queries_per_segment": 1,
                        "max_search_specs_per_segment": rules["max_search_specs_per_cluster"],
                    },
                    is_experimental_probe=True,
                    reason_prefix="experimental",
                )
            )
    return specs


def _select_experimental_communities(
    cluster: dict[str, object],
    *,
    used_communities: set[str],
    max_scope_communities: int,
) -> list[str]:
    selected: list[str] = []
    for raw in _as_list(cluster.get("experimental_communities")):
        community = str(raw).strip()
        key = community.lower()
        if not community or key in used_communities:
            continue
        if len(used_communities) >= max_scope_communities:
            break
        used_communities.add(key)
        selected.append(community)
    return selected


def _build_search_specs(
    scope_id: SourceScopeId,
    topic_pack_id: str,
    subreddits: list[str],
    keyword_buckets: dict[str, list[str]],
    payload: dict[str, object],
    *,
    is_experimental_probe: bool = False,
    reason_prefix: str | None = None,
) -> list[RedditSearchSpec]:
    specs: list[RedditSearchSpec] = []
    search_defaults = _as_mapping(payload["search_defaults"])
    bucket_order = tuple(str(item) for item in _as_list(payload["bucket_priority"]))
    selected_subreddits, selected_queries = allocate_search_inputs(
        subreddits,
        keyword_buckets,
        list(bucket_order),
        _as_str_list(payload.get("search_templates")),
        subreddit_limit=_int(payload.get("search_subreddit_limit"), default=3),
        keywords_per_bucket=_int(payload.get("keywords_per_bucket"), default=2),
        template_limit=_int(payload.get("template_queries_per_segment"), default=3),
        spec_limit=_int(payload.get("max_search_specs_per_segment"), default=24),
    )
    keyword_lookup = {
        keyword: bucket
        for bucket in bucket_order
        for keyword in list(keyword_buckets.get(bucket) or [])
    }
    for query in selected_queries:
        primary_reason = f"{topic_pack_id}:template_query"
        if query in keyword_lookup:
            primary_reason = f"{topic_pack_id}:{keyword_lookup[query]}_keyword"
        if reason_prefix:
            primary_reason = f"{topic_pack_id}:{reason_prefix}_{primary_reason.split(':', 1)[1]}"
        for subreddit in selected_subreddits:
            specs.append(
                RedditSearchSpec(
                    source_scope_id=scope_id,
                    topic_pack_id=topic_pack_id,
                    topic_cluster_id=str(payload.get("topic_cluster_id") or "") or None,
                    topic_cluster_ids=_as_str_list(payload.get("topic_cluster_ids")),
                    subreddit=subreddit,
                    mode="search",
                    sort=str(search_defaults["sort"]),
                    time_filter=_time_filter(search_defaults["time_filter"]),
                    query=str(query),
                    listing_source=f"search:{search_defaults['sort']}:{search_defaults['time_filter']}",
                    primary_reason=primary_reason,
                    matched_keywords=[str(query)],
                    is_experimental_probe=is_experimental_probe,
                )
            )
    return specs


def _build_listing_specs(
    scope_id: SourceScopeId,
    topic_pack_id: str,
    subreddits: list[str],
    payload: dict[str, object],
    *,
    is_experimental_probe: bool = False,
    reason_prefix: str | None = None,
) -> list[RedditSearchSpec]:
    selected_subreddits, selected_rules = allocate_listing_inputs(
        subreddits,
        _listing_rules(payload["listing_rules"]),
        subreddit_limit=_int(payload.get("listing_subreddit_limit"), default=3),
        spec_limit=_int(payload.get("max_listing_specs_per_segment"), default=9),
    )
    return [
        RedditSearchSpec(
            source_scope_id=scope_id,
            topic_pack_id=topic_pack_id,
            topic_cluster_id=str(payload.get("topic_cluster_id") or "") or None,
            topic_cluster_ids=_as_str_list(payload.get("topic_cluster_ids")),
            subreddit=subreddit,
            mode="listing",
            sort=sort,
            time_filter=_time_filter(time_filter),
            listing_source=f"listing:{sort}:{time_filter}",
            primary_reason=_listing_primary_reason(
                scope_id=scope_id,
                topic_pack_id=topic_pack_id,
                sort=sort,
                reason_prefix=reason_prefix,
            ),
            is_experimental_probe=is_experimental_probe,
        )
        for subreddit in selected_subreddits
        for sort, time_filter in selected_rules
    ]


def _listing_primary_reason(
    *,
    scope_id: SourceScopeId,
    topic_pack_id: str,
    sort: str,
    reason_prefix: str | None,
) -> str:
    base = (
        "listing_keyword_bridge"
        if uses_growth_pack_intake_path(scope_id, topic_pack_id)
        else f"listing_{sort}"
    )
    if reason_prefix:
        base = f"{reason_prefix}_{base}"
    return f"{topic_pack_id}:{base}"


def _as_list(value: object) -> list[object]:
    return list(cast(Iterable[object], value or []))


def _as_str_list(value: object) -> list[str]:
    return [str(item) for item in _as_list(value)]


def _as_mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value or {}))


def _listing_rules(value: object) -> list[tuple[str, str]]:
    return [(str(sort), str(time_filter)) for sort, time_filter in cast(Iterable[tuple[object, object]], value or [])]


def _int(value: object, *, default: int) -> int:
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    return default


def _time_filter(value: object) -> TimeFilter:
    return cast(TimeFilter, str(value))


def _ordered_topic_packs(scope_id: SourceScopeId) -> list[TopicPack]:
    packs = get_scope_topic_packs(scope_id)
    return sorted(
        packs,
        key=lambda pack: (0 if uses_growth_pack_intake_path(scope_id, pack.topic_pack_id) else 1),
    )


__all__ = ["build_reddit_search_specs"]
