from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Optional, Any, cast

from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.hotpost_supply_contract import get_supply_scope
from app.services.hotpost.named_topic_watchlist import NamedTopicWatch, load_named_topic_registry


_PACK_ID_HINT_FIELDS = ("primary_reason", "query")
_GROWTH_LISTING_BRIDGE_PACKS = {"organic-discovery", "funnel-conversion"}


def normalize_topic_metadata(
    *,
    topic_pack_id:Optional[ str],
    topic_cluster_id:Optional[ str],
    topic_cluster_ids:Optional[ Iterable[str]],
    named_topic_ids:Optional[ Iterable[str]],
) -> dict[str, Any]:
    cluster_ids = _dedupe_strings(topic_cluster_ids or ())
    if topic_cluster_id and topic_cluster_id not in cluster_ids:
        cluster_ids = [topic_cluster_id, *cluster_ids]
    named_ids = _dedupe_strings(named_topic_ids or ())
    resolved_cluster_id = str(topic_cluster_id or "").strip() or (cluster_ids[0] if cluster_ids else None)
    resolved_pack_id = str(topic_pack_id or "").strip() or None
    return {
        "topic_pack_id": resolved_pack_id,
        "topic_cluster_id": resolved_cluster_id,
        "topic_cluster_ids": cluster_ids,
        "named_topic_ids": named_ids,
    }


def build_candidate_metadata_lookup(candidates: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in candidates:
        candidate_id = str(item.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        lookup[candidate_id] = resolve_topic_metadata(item)
    return lookup


def resolve_topic_metadata(
    item: Mapping[str, Any],
    *,
    candidate_lookup:Optional[ Mapping[str, Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    metadata = normalize_topic_metadata(
        topic_pack_id=_optional_str(item.get("topic_pack_id")),
        topic_cluster_id=_optional_str(item.get("topic_cluster_id")),
        topic_cluster_ids=_string_list(item.get("topic_cluster_ids")),
        named_topic_ids=_string_list(item.get("named_topic_ids")),
    )
    inherited = _inherit_candidate_metadata(item, candidate_lookup or {})
    metadata = _merge_topic_metadata(metadata, inherited)
    scope_id = _optional_scope_id(item.get("source_scope_id"))
    if scope_id is None:
        return metadata

    text_blob = _item_text_blob(item)
    communities = _item_communities(item)
    primary_reason = _pack_hint(item)
    if (
        metadata["topic_pack_id"] is not None
        and not metadata["named_topic_ids"]
        and ":listing_" in primary_reason
        and not _should_preserve_listing_bridge_pack(
            scope_id=scope_id,
            topic_pack_id=metadata["topic_pack_id"],
            primary_reason=primary_reason,
        )
    ):
        semantic_pack_id = _infer_topic_pack_id(
            scope_id,
            text_blob=text_blob,
            communities=communities,
            primary_reason=primary_reason,
        )
        if semantic_pack_id and semantic_pack_id != metadata["topic_pack_id"]:
            metadata["topic_pack_id"] = semantic_pack_id
            metadata["topic_cluster_id"] = None
            metadata["topic_cluster_ids"] = []
    if metadata["topic_pack_id"] is None:
        metadata["topic_pack_id"] = _infer_topic_pack_id(
            scope_id,
            text_blob=text_blob,
            communities=communities,
            primary_reason=primary_reason,
        )

    named_ids = list(metadata["named_topic_ids"])
    if not named_ids:
        named_ids = _infer_named_topic_ids(
            scope_id,
            topic_pack_id=metadata["topic_pack_id"],
            text_blob=text_blob,
            matched_keywords=_string_list(item.get("matched_keywords")),
        )
        metadata["named_topic_ids"] = named_ids

    if named_ids:
        watch_clusters: list[str] = []
        watch_packs: list[str] = []
        for topic_id in named_ids:
            watch = _named_topic_registry().get(topic_id)
            if watch is None:
                continue
            watch_clusters.extend(watch.topic_cluster_ids)
            watch_packs.append(watch.topic_pack_id)
        if metadata["topic_pack_id"] is None and len(set(watch_packs)) == 1:
            metadata["topic_pack_id"] = watch_packs[0]
        metadata["topic_cluster_ids"] = _dedupe_strings([*metadata["topic_cluster_ids"], *watch_clusters])

    if not metadata["topic_cluster_ids"]:
        metadata["topic_cluster_ids"] = _infer_topic_cluster_ids(
            scope_id,
            topic_pack_id=metadata["topic_pack_id"],
            text_blob=text_blob,
            communities=communities,
        )
    if metadata["topic_cluster_id"] is None and metadata["topic_cluster_ids"]:
        metadata["topic_cluster_id"] = metadata["topic_cluster_ids"][0]
    return normalize_topic_metadata(**metadata)


def merge_topic_metadata(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    merged_pack_ids: list[str] = []
    merged_cluster_ids: list[str] = []
    merged_named_ids: list[str] = []
    for item in items:
        metadata = resolve_topic_metadata(item)
        if metadata["topic_pack_id"]:
            merged_pack_ids.append(str(metadata["topic_pack_id"]))
        merged_cluster_ids.extend(metadata["topic_cluster_ids"])
        merged_named_ids.extend(metadata["named_topic_ids"])
    pack_id = Counter(merged_pack_ids).most_common(1)[0][0] if merged_pack_ids else None
    return normalize_topic_metadata(
        topic_pack_id=pack_id,
        topic_cluster_id=None,
        topic_cluster_ids=Counter(merged_cluster_ids).keys(),
        named_topic_ids=merged_named_ids,
    )


def _merge_topic_metadata(base: dict[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    pack_id = base["topic_pack_id"] or _optional_str(incoming.get("topic_pack_id"))
    cluster_ids = _dedupe_strings([*base["topic_cluster_ids"], *_string_list(incoming.get("topic_cluster_ids"))])
    cluster_id = base["topic_cluster_id"] or _optional_str(incoming.get("topic_cluster_id"))
    named_ids = _dedupe_strings([*base["named_topic_ids"], *_string_list(incoming.get("named_topic_ids"))])
    return normalize_topic_metadata(
        topic_pack_id=pack_id,
        topic_cluster_id=cluster_id,
        topic_cluster_ids=cluster_ids,
        named_topic_ids=named_ids,
    )


def _inherit_candidate_metadata(
    item: Mapping[str, Any],
    candidate_lookup: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not candidate_lookup:
        return normalize_topic_metadata(
            topic_pack_id=None,
            topic_cluster_id=None,
            topic_cluster_ids=[],
            named_topic_ids=[],
        )
    rows: list[Mapping[str, Any]] = []
    for candidate_id in _candidate_ids_from_item(item):
        row = candidate_lookup.get(candidate_id)
        if row is not None:
            rows.append(row)
    if not rows:
        return normalize_topic_metadata(
            topic_pack_id=None,
            topic_cluster_id=None,
            topic_cluster_ids=[],
            named_topic_ids=[],
        )
    return merge_topic_metadata(rows)


def _candidate_ids_from_item(item: Mapping[str, Any]) -> list[str]:
    candidate_ids = _string_list(item.get("candidate_ids"))
    single = _optional_str(item.get("candidate_id"))
    if single:
        candidate_ids.append(single)
    card_id = _optional_str(item.get("card_id"))
    if card_id and card_id.startswith("card-cand-"):
        for suffix in ("-validate", "-write"):
            if card_id.endswith(suffix):
                candidate_ids.append(card_id[len("card-") : -len(suffix)])
                break
    return _dedupe_strings(candidate_ids)


def _pack_hint(item: Mapping[str, Any]) -> str:
    for field_name in _PACK_ID_HINT_FIELDS:
        value = _optional_str(item.get(field_name))
        if value:
            return value
    return ""


def _infer_topic_pack_id(
    scope_id: SourceScopeId,
    *,
    text_blob: str,
    communities: set[str],
    primary_reason: str,
) ->Optional[ str]:
    pack_hint = primary_reason.split(":", 1)[0].strip().lower()
    if _should_preserve_listing_bridge_pack(
        scope_id=scope_id,
        topic_pack_id=pack_hint,
        primary_reason=primary_reason,
    ):
        return pack_hint
    pack_ids = _scope_topic_pack_ids(scope_id)
    cluster_scores = _cluster_scores(scope_id, text_blob=text_blob, communities=communities)
    pack_scores: Counter[str] = Counter()
    for cluster_id, score in cluster_scores.items():
        if score <= 0:
            continue
        for pack_id in _cluster_registry(scope_id)[cluster_id]["pack_ids"]:
            pack_scores[pack_id] += score
    listing_reason = ":listing_" in primary_reason
    if listing_reason and cluster_scores:
        ranked_clusters = [
            (cluster_id, score)
            for cluster_id, score in sorted(cluster_scores.items(), key=lambda item: (-item[1], item[0]))
            if score > 0
        ]
        if ranked_clusters:
            cluster_id, score = ranked_clusters[0]
            pack_options = _cluster_registry(scope_id)[cluster_id]["pack_ids"]
            if score >= 9 and pack_options:
                return pack_options[0]
    if pack_hint in pack_ids:
        return pack_hint
    if not pack_scores:
        return None
    pack_id, score = pack_scores.most_common(1)[0]
    return pack_id if score > 0 else None


def _should_preserve_listing_bridge_pack(
    *,
    scope_id: SourceScopeId,
    topic_pack_id: Optional[str],
    primary_reason: str,
) -> bool:
    pack_id = str(topic_pack_id or "").strip().lower()
    return (
        scope_id == "business-growth-ops"
        and pack_id in _GROWTH_LISTING_BRIDGE_PACKS
        and primary_reason.endswith(":listing_keyword_bridge")
    )


def _infer_topic_cluster_ids(
    scope_id: SourceScopeId,
    *,
    topic_pack_id:Optional[ str],
    text_blob: str,
    communities: set[str],
) -> list[str]:
    scores = _cluster_scores(
        scope_id,
        text_blob=text_blob,
        communities=communities,
        topic_pack_id=topic_pack_id,
    )
    ranked = [cluster_id for cluster_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if score > 0]
    return ranked[:2]


def _infer_named_topic_ids(
    scope_id: SourceScopeId,
    *,
    topic_pack_id:Optional[ str],
    text_blob: str,
    matched_keywords: list[str],
) -> list[str]:
    explicit = {_normalize_text(keyword) for keyword in matched_keywords}
    matched: list[str] = []
    for topic_id, watch in _named_topic_registry().items():
        if watch.scope_id != scope_id:
            continue
        if topic_pack_id and watch.topic_pack_id != topic_pack_id:
            continue
        if topic_id in explicit:
            matched.append(topic_id)
            continue
        if any(_normalize_text(query) in text_blob for query in watch.queries):
            matched.append(topic_id)
    return _dedupe_strings(matched)


def _cluster_scores(
    scope_id: SourceScopeId,
    *,
    text_blob: str,
    communities: set[str],
    topic_pack_id:Optional[ str] = None,
) -> dict[str, int]:
    scores: dict[str, int] = {}
    for cluster_id, metadata in _cluster_registry(scope_id).items():
        if topic_pack_id and topic_pack_id not in metadata["pack_ids"]:
            continue
        score = 0
        community_hits = len(communities & metadata["communities"])
        if community_hits:
            score += community_hits * 5
        phrase_hits = 0
        for phrase in metadata["phrases"]:
            if phrase in text_blob:
                phrase_hits += 1
        if phrase_hits:
            score += min(phrase_hits, 4) * 3
        cluster_label = _normalize_text(cluster_id.replace("-", " "))
        if cluster_label and cluster_label in text_blob:
            score += 2
        scores[cluster_id] = score
    return scores


@lru_cache(maxsize=None)
def _cluster_registry(scope_id: SourceScopeId) -> dict[str, dict[str, Any]]:
    scope = get_supply_scope(scope_id)
    clusters = dict(scope.get("topic_clusters") or {})
    topic_packs = dict(scope.get("topic_packs") or {})
    cluster_to_pack_ids: dict[str, set[str]] = defaultdict(set)
    for pack_id, pack in topic_packs.items():
        for cluster_id in list(pack.get("topic_clusters") or []):
            cluster_to_pack_ids[str(cluster_id)].add(str(pack_id))
    registry: dict[str, dict[str, Any]] = {}
    for cluster_id, raw in clusters.items():
        phrases: list[str] = []
        for tag in list(raw.get("tags") or []):
            normalized = _normalize_text(str(tag).replace("-", " "))
            if normalized:
                phrases.append(normalized)
        for entity in list(raw.get("named_entities") or []):
            normalized = _normalize_text(str(entity))
            if normalized:
                phrases.append(normalized)
        for values in dict(raw.get("keyword_buckets") or {}).values():
            for value in list(values or []):
                normalized = _normalize_text(str(value))
                if normalized:
                    phrases.append(normalized)
        for stems in dict(raw.get("search_templates") or {}).values():
            for stem in list(stems or []):
                normalized = _normalize_text(str(stem))
                if normalized:
                    phrases.append(normalized)
        communities = {
            _normalize_community(value)
            for key in ("primary_communities", "candidate_communities", "listing_communities")
            for value in list(raw.get(key) or [])
            if _normalize_community(value)
        }
        registry[str(cluster_id)] = {
            "pack_ids": tuple(sorted(cluster_to_pack_ids.get(str(cluster_id), set()))),
            "communities": communities,
            "phrases": tuple(sorted(_dedupe_strings(phrases))),
        }
    return registry


@lru_cache(maxsize=None)
def _scope_topic_pack_ids(scope_id: SourceScopeId) -> tuple[str, ...]:
    scope = get_supply_scope(scope_id)
    return tuple(sorted(str(pack_id) for pack_id in dict(scope.get("topic_packs") or {}).keys()))


@lru_cache(maxsize=1)
def _named_topic_registry() -> dict[str, NamedTopicWatch]:
    return load_named_topic_registry()


def _item_text_blob(item: Mapping[str, Any]) -> str:
    fragments: list[str] = []
    for key in (
        "title",
        "summary_line",
        "why_now",
        "audience",
        "query",
        "primary_reason",
        "listing_source",
    ):
        value = _optional_str(item.get(key))
        if value:
            fragments.append(value)
    fragments.extend(_string_list(item.get("matched_keywords")))
    fragments.extend(_string_list(item.get("intent_tags")))
    detail = item.get("detail")
    if isinstance(detail, Mapping):
        fragments.extend(_nested_strings(detail))
    for key in ("evidence_quotes", "quotes"):
        value = item.get(key)
        if isinstance(value, list):
            for row in value:
                if isinstance(row, Mapping):
                    fragments.extend(_nested_strings(row))
    preview_quote = item.get("preview_quote")
    if isinstance(preview_quote, Mapping):
        fragments.extend(_nested_strings(preview_quote))
    return " ".join(_normalize_text(value) for value in fragments if _normalize_text(value))


def _item_communities(item: Mapping[str, Any]) -> set[str]:
    communities = {
        _normalize_community(item.get("matched_subreddit")),
        _normalize_community(item.get("top_community")),
    }
    communities.update(_normalize_community(value) for value in _string_list(item.get("source_communities")))
    for key in ("evidence_quotes", "quotes"):
        value = item.get(key)
        if isinstance(value, list):
            for row in value:
                if isinstance(row, Mapping):
                    communities.add(_normalize_community(row.get("community")))
    preview_quote = item.get("preview_quote")
    if isinstance(preview_quote, Mapping):
        communities.add(_normalize_community(preview_quote.get("community")))
    return {value for value in communities if value}


def _nested_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = _optional_str(value)
        return [normalized] if normalized else []
    if isinstance(value, Mapping):
        items: list[str] = []
        for item in value.values():
            items.extend(_nested_strings(item))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_nested_strings(item))
        return items
    return []


def _normalize_text(value:Optional[ str]) -> str:
    return " ".join(str(value or "").strip().lower().replace('"', "").replace("“", "").replace("”", "").split())


def _normalize_community(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("r/"):
        normalized = normalized[2:]
    return normalized


def _optional_str(value: Any) ->Optional[ str]:
    normalized = str(value or "").strip()
    return normalized or None


def _optional_scope_id(value: Any) ->Optional[ SourceScopeId]:
    normalized = _optional_str(value)
    if normalized is None:
        return None
    return cast(SourceScopeId, normalized)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe_strings(str(item).strip() for item in value if str(item).strip())


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


__all__ = [
    "build_candidate_metadata_lookup",
    "merge_topic_metadata",
    "normalize_topic_metadata",
    "resolve_topic_metadata",
]
