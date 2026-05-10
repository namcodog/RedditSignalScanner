from __future__ import annotations

from typing import Any

from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.hotpost_supply_contract import (
    get_scope_topic_pack_contracts,
    get_supply_collect_defaults,
    get_supply_global_rules,
    get_supply_scope,
    get_topic_pack_contract,
)


def get_supply_scope_meta(scope_id: SourceScopeId) -> dict[str, str]:
    scope = get_supply_scope(scope_id)
    return {"title": str(scope["title"]), "description": str(scope["description"])}


def build_topic_pack_payloads(scope_id: SourceScopeId) -> list[dict[str, Any]]:
    scope = get_supply_scope(scope_id)
    clusters = dict(scope.get("topic_clusters") or {})
    rules = get_supply_global_rules()
    collect_defaults = get_supply_collect_defaults()
    payloads: list[dict[str, Any]] = []
    for topic_pack_id, pack in get_scope_topic_pack_contracts(scope_id).items():
        refs = [dict(clusters[name]) for name in list(pack.get("topic_clusters") or []) if name in clusters]
        keywords = _merge_keyword_buckets(refs)
        entities = _merge_strings(refs, "named_entities")
        if entities:
            keywords.setdefault("entity", [])
            keywords["entity"].extend(entities)
            keywords["entity"] = _dedupe(keywords["entity"])
        subreddits = _merge_strings(refs, "primary_communities", "candidate_communities")
        search_templates = _merge_search_templates(refs, rules)
        cluster_segments = [_build_cluster_segment(name, dict(clusters[name]), rules, pack, collect_defaults) for name in list(pack.get("topic_clusters") or []) if name in clusters]
        payloads.append(
            {
                "topic_pack_id": topic_pack_id,
                "title": str(pack["title"]),
                "description": str(pack["description"]),
                "target_share": int(pack["target_share"]),
                "subreddits": subreddits,
                "keywords": keywords,
                "source_mode": _required_str(pack, "source_mode", name=f"{scope_id}.{topic_pack_id}"),
                "allow_listing": _required_bool(pack, "allow_listing", name=f"{scope_id}.{topic_pack_id}"),
                "allow_search_hot": _required_bool(pack, "allow_search_hot", name=f"{scope_id}.{topic_pack_id}"),
                "bucket_priority": [str(item) for item in _required_list(pack, "bucket_priority", name=f"{scope_id}.{topic_pack_id}")],
                "candidate_cap": _required_int(pack, "candidate_cap", name=f"{scope_id}.{topic_pack_id}"),
                "search_fetch_limit": _inherited_int(pack, collect_defaults, key="search_fetch_limit", name=f"{scope_id}.{topic_pack_id}"),
                "listing_fetch_limit": _inherited_int(pack, collect_defaults, key="listing_fetch_limit", name=f"{scope_id}.{topic_pack_id}"),
                "comments_fetch_limit": _inherited_int(pack, collect_defaults, key="comments_fetch_limit", name=f"{scope_id}.{topic_pack_id}"),
                "subreddit_candidate_cap": _inherited_int(pack, collect_defaults, key="subreddit_candidate_cap", name=f"{scope_id}.{topic_pack_id}"),
                "search_subreddit_limit": _inherited_int(pack, collect_defaults, key="search_subreddit_limit", name=f"{scope_id}.{topic_pack_id}"),
                "listing_subreddit_limit": _inherited_int(pack, collect_defaults, key="listing_subreddit_limit", name=f"{scope_id}.{topic_pack_id}"),
                "keywords_per_bucket": _inherited_int(pack, collect_defaults, key="keywords_per_bucket", name=f"{scope_id}.{topic_pack_id}"),
                "template_queries_per_segment": _inherited_int(pack, collect_defaults, key="template_queries_per_segment", name=f"{scope_id}.{topic_pack_id}"),
                "max_search_specs_per_segment": _inherited_int(pack, collect_defaults, key="max_search_specs_per_segment", name=f"{scope_id}.{topic_pack_id}"),
                "max_listing_specs_per_segment": _inherited_int(pack, collect_defaults, key="max_listing_specs_per_segment", name=f"{scope_id}.{topic_pack_id}"),
                "listing_rules": [
                    tuple((str(item["sort"]), str(item["time_filter"])))
                    for item in list(pack.get("listing_rules") or _required_list(rules, "listing_rules_default", name="global_rules"))
                ],
                "listing_bridge_communities": [str(item) for item in list(pack.get("listing_bridge_communities") or [])],
                "listing_bridge_rules": [
                    tuple((str(item["sort"]), str(item["time_filter"])))
                    for item in list(pack.get("listing_bridge_rules") or [])
                ],
                "search_defaults": dict(rules["search_defaults"]),
                "search_templates": search_templates,
                "cluster_segments": cluster_segments,
                "noise_subreddits": [str(item).lower() for item in list(pack.get("noise_subreddits") or [])],
                "noise_markers": [str(item).lower() for item in list(pack.get("noise_markers") or [])],
            }
        )
    return payloads


def get_topic_pack_payload(scope_id: SourceScopeId, topic_pack_id: str) -> dict[str, Any]:
    for payload in build_topic_pack_payloads(scope_id):
        if payload["topic_pack_id"] == topic_pack_id:
            return payload
    raise KeyError(f"Unknown topic pack payload: {scope_id}/{topic_pack_id}")


def _merge_keyword_buckets(cluster_refs: list[dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for cluster in cluster_refs:
        for bucket, values in dict(cluster.get("keyword_buckets") or {}).items():
            merged.setdefault(str(bucket), [])
            merged[str(bucket)].extend(str(item) for item in list(values))
    return {bucket: _dedupe(values) for bucket, values in merged.items()}


def _merge_strings(cluster_refs: list[dict[str, Any]], *keys: str) -> list[str]:
    merged: list[str] = []
    for cluster in cluster_refs:
        for key in keys:
            merged.extend(str(item) for item in list(cluster.get(key) or []))
    return _dedupe(merged)


def _merge_search_templates(cluster_refs: list[dict[str, Any]], rules: dict[str, Any]) -> list[str]:
    template_sets = dict(rules.get("search_template_sets") or {})
    queries: list[str] = []
    for cluster in cluster_refs:
        for set_name, stems in dict(cluster.get("search_templates") or {}).items():
            patterns = [str(item) for item in list(template_sets.get(set_name) or [])]
            for stem in list(stems):
                for pattern in patterns:
                    queries.append(pattern.format(stem=str(stem)))
    return _dedupe(queries)


def _build_cluster_segment(
    cluster_id: str,
    cluster: dict[str, Any],
    rules: dict[str, Any],
    pack: dict[str, Any],
    collect_defaults: dict[str, Any],
) -> dict[str, Any]:
    keywords = _merge_keyword_buckets([cluster])
    entities = _merge_strings([cluster], "named_entities")
    if entities:
        keywords.setdefault("entity", [])
        keywords["entity"].extend(entities)
        keywords["entity"] = _dedupe(keywords["entity"])
    return {
        "cluster_id": cluster_id,
        "subreddits": _merge_strings([cluster], "primary_communities", "candidate_communities"),
        "search_subreddits": _merge_strings([cluster], "primary_communities", "candidate_communities"),
        "listing_subreddits": _dedupe(
            [str(item) for item in list(cluster.get("listing_communities") or [])]
            or _merge_strings([cluster], "primary_communities", "candidate_communities")
        ),
        "allow_listing": _inherited_bool(cluster, pack, "allow_listing", name=cluster_id),
        "keywords": keywords,
        "bucket_priority": [
            str(item)
            for item in _inherited_list(cluster, pack, key="bucket_priority", name=cluster_id)
        ],
        "source_mode": _inherited_str(cluster, pack, "source_mode", name=cluster_id),
        "listing_rules": [
            tuple((str(item["sort"]), str(item["time_filter"])))
            for item in list(cluster.get("listing_rules") or pack.get("listing_rules") or rules["listing_rules_default"])
        ],
        "search_templates": _merge_search_templates([cluster], rules),
        "search_subreddit_limit": _inherited_int(cluster, pack, collect_defaults, key="search_subreddit_limit", name=cluster_id),
        "listing_subreddit_limit": _inherited_int(cluster, pack, collect_defaults, key="listing_subreddit_limit", name=cluster_id),
        "keywords_per_bucket": _inherited_int(cluster, pack, collect_defaults, key="keywords_per_bucket", name=cluster_id),
        "template_queries_per_segment": _inherited_int(cluster, pack, collect_defaults, key="template_queries_per_segment", name=cluster_id),
        "max_search_specs_per_segment": _inherited_int(cluster, pack, collect_defaults, key="max_search_specs_per_segment", name=cluster_id),
        "max_listing_specs_per_segment": _inherited_int(cluster, pack, collect_defaults, key="max_listing_specs_per_segment", name=cluster_id),
        "search_fetch_limit": _inherited_int(cluster, pack, collect_defaults, key="search_fetch_limit", name=cluster_id),
        "listing_fetch_limit": _inherited_int(cluster, pack, collect_defaults, key="listing_fetch_limit", name=cluster_id),
        "comments_fetch_limit": _inherited_int(cluster, pack, collect_defaults, key="comments_fetch_limit", name=cluster_id),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _required_int(raw: dict[str, Any], key: str, *, name: str) -> int:
    if key not in raw:
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return int(raw[key])


def _required_str(raw: dict[str, Any], key: str, *, name: str) -> str:
    if key not in raw:
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return str(raw[key])


def _required_bool(raw: dict[str, Any], key: str, *, name: str) -> bool:
    if key not in raw:
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return bool(raw[key])


def _required_list(raw: dict[str, Any], key: str, *, name: str) -> list[Any]:
    if key not in raw or not isinstance(raw[key], list):
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return list(raw[key])


def _inherited_list(child: dict[str, Any], parent: dict[str, Any], *, key: str, name: str) -> list[Any]:
    if key in child and isinstance(child[key], list):
        return list(child[key])
    if key in parent and isinstance(parent[key], list):
        return list(parent[key])
    raise ValueError(f"hotpost_supply_discovery_v2.yaml missing inherited {name}.{key}")


def _inherited_int(*sources: dict[str, Any], key: str, name: str) -> int:
    for source in sources:
        if key in source:
            return int(source[key])
    raise ValueError(f"hotpost_supply_discovery_v2.yaml missing inherited {name}.{key}")


def _inherited_str(child: dict[str, Any], parent: dict[str, Any], key: str, *, name: str) -> str:
    if key in child:
        return str(child[key])
    if key in parent:
        return str(parent[key])
    raise ValueError(f"hotpost_supply_discovery_v2.yaml missing inherited {name}.{key}")


def _inherited_bool(child: dict[str, Any], parent: dict[str, Any], key: str, *, name: str) -> bool:
    if key in child:
        return bool(child[key])
    if key in parent:
        return bool(parent[key])
    raise ValueError(f"hotpost_supply_discovery_v2.yaml missing inherited {name}.{key}")


__all__ = ["build_topic_pack_payloads", "get_supply_scope_meta", "get_topic_pack_payload"]
