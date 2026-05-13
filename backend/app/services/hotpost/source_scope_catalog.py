from __future__ import annotations

from math import floor

from app.schemas.hotpost_source_scopes import SourceScope, TopicPack
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.hotpost_supply_projection import build_topic_pack_payloads, get_supply_scope_meta


def list_source_scopes() -> list[SourceScope]:
    return [_build_scope(scope_id) for scope_id in ("ai-automation", "ecommerce-sellers", "business-growth-ops")]


def get_source_scope(scope_id: SourceScopeId) -> SourceScope:
    return _build_scope(scope_id)


def get_scope_topic_packs(scope_id: SourceScopeId) -> list[TopicPack]:
    return [_build_topic_pack(item) for item in build_topic_pack_payloads(scope_id)]


def get_scope_keywords(scope_id: SourceScopeId) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for pack in build_topic_pack_payloads(scope_id):
        for bucket, values in _pack_keywords(pack).items():
            merged.setdefault(bucket, [])
            merged[bucket].extend(values)
    return {bucket: _dedupe(values) for bucket, values in merged.items()}


def get_topic_pack_keyword_buckets(scope_id: SourceScopeId, topic_pack_id: str) -> dict[str, list[str]]:
    for pack in build_topic_pack_payloads(scope_id):
        if pack["topic_pack_id"] == topic_pack_id:
            return _pack_keywords(pack)
    raise KeyError(f"Unknown topic pack: {scope_id}/{topic_pack_id}")


def build_topic_pack_candidate_quotas(scope_id: SourceScopeId, max_candidates: int) -> dict[str, int]:
    packs = get_scope_topic_packs(scope_id)
    raw = {pack.topic_pack_id: max_candidates * pack.target_share / 100 for pack in packs}
    quotas = {pack.topic_pack_id: floor(raw[pack.topic_pack_id]) for pack in packs}
    remaining = max_candidates - sum(quotas.values())
    remainders = sorted(
        ((pack.topic_pack_id, raw[pack.topic_pack_id] - quotas[pack.topic_pack_id]) for pack in packs),
        key=lambda item: item[1],
        reverse=True,
    )
    for topic_pack_id, _ in remainders:
        if remaining <= 0:
            break
        quotas[topic_pack_id] += 1
        remaining -= 1
    return quotas


def _build_scope(scope_id: SourceScopeId) -> SourceScope:
    meta = get_supply_scope_meta(scope_id)
    topic_packs = get_scope_topic_packs(scope_id)
    subreddits = _dedupe(item for pack in topic_packs for item in pack.subreddits)
    search_queries = _dedupe(item for pack in topic_packs for item in pack.search_queries)
    return SourceScope(
        source_scope_id=scope_id,
        title=meta["title"],
        description=meta["description"],
        subreddits=subreddits,
        search_queries=search_queries,
        topic_packs=topic_packs,
    )


def _build_topic_pack(pack: dict[str, object]) -> TopicPack:
    keywords = _pack_keywords(pack)
    queries = _dedupe([item for values in keywords.values() for item in values] + list(pack.get("search_templates") or []))
    return TopicPack(
        topic_pack_id=str(pack["topic_pack_id"]),
        title=str(pack["title"]),
        description=str(pack["description"]),
        target_share=int(pack["target_share"]),
        subreddits=list(pack["subreddits"]),
        search_queries=queries,
    )


def _pack_keywords(pack: dict[str, object]) -> dict[str, list[str]]:
    return {bucket: list(values) for bucket, values in dict(pack["keywords"]).items()}


def _dedupe(items) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


__all__ = [
    "build_topic_pack_candidate_quotas",
    "get_scope_keywords",
    "get_scope_topic_packs",
    "get_source_scope",
    "get_topic_pack_keyword_buckets",
    "list_source_scopes",
]
