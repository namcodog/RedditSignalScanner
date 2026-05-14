from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from app.services.community.community_recommendation_models import (
    HISTORICAL_DEPTH,
    READY,
    WATCHING,
    CapabilityTag,
    CommunityActivitySnapshot,
    CommunitySignal,
)
from app.services.community.community_recommendation_utils import (
    dedupe,
    latest_activity,
    normalize_text,
    tokenize,
)
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    InterestTagDefinition,
    RecommendationPolicy,
    load_interest_tag_catalog,
)
from app.services.hotpost.hotpost_community_activity import normalize_community_key


def term_hit_count(keys: Iterable[str], values: Iterable[str]) -> int:
    text = " ".join(values).lower()
    tokens = tokenize(text)
    hits = 0
    for keyword in keys:
        key = normalize_text(keyword)
        if key in tokens or (len(key) >= 5 and any(t.startswith(key) for t in tokens)):
            hits += 1
    return hits


def community_key_hit_count(keys: Iterable[str], signal: CommunitySignal) -> int:
    hits = 0
    for keyword in keys:
        key = normalize_text(keyword)
        if len(key) >= 4 and key in signal.key:
            hits += 1
        elif len(key) == 3 and signal.key in {key, f"{key}s"}:
            hits += 1
    return hits


def has_recommendation_evidence(signal: CommunitySignal) -> bool:
    return (
        signal.semantic_observations
        + signal.content_labels
        + signal.content_entities
        + signal.hotpost_cards
        + signal.historical_posts
        + signal.recent_posts_15d
    ) > 0


def community_status(signal: CommunitySignal) -> str:
    evidence = (
        signal.semantic_observations
        + signal.content_labels
        + signal.content_entities
        + signal.hotpost_cards
        + signal.historical_posts
    )
    if signal.recent_posts_15d > 0 and evidence > 0:
        return READY
    if signal.historical_posts > 0 or signal.semantic_observations > 0:
        return HISTORICAL_DEPTH
    return WATCHING


def evidence_sources_for_signal(signal: CommunitySignal) -> tuple[str, ...]:
    sources = ["community_pool"]
    if signal.source_refs:
        sources.append("source_refs")
    if signal.categories or signal.keywords:
        sources.append("community_pool_semantic_profile")
    if signal.semantic_observations:
        sources.append("semantic_observation")
    if signal.semantic_terms:
        sources.append("semantic_terms")
    if signal.content_labels:
        sources.append("content_labels")
    if signal.content_entities:
        sources.append("content_entities")
    if signal.brand_terms:
        sources.append("brand_system_evidence")
    if signal.recent_posts_15d:
        sources.append("recent_activity_15d")
    if signal.recent_activity_source:
        sources.append(signal.recent_activity_source)
    if signal.historical_posts:
        sources.append("historical_posts")
    if signal.hotpost_cards:
        sources.append("hotpost_published_cards")
    return tuple(sources)


def merge_activity_snapshots(
    signals: Iterable[CommunitySignal],
    snapshots: Iterable[CommunityActivitySnapshot],
) -> tuple[CommunitySignal, ...]:
    by_key = {
        normalize_community_key(s.community): s
        for s in snapshots
        if normalize_community_key(s.community)
    }
    merged: list[CommunitySignal] = []
    for signal in signals:
        snapshot = by_key.get(signal.key)
        if snapshot is None:
            merged.append(signal)
            continue
        merged.append(
            replace(
                signal,
                recent_posts_15d=max(
                    signal.recent_posts_15d, snapshot.recent_posts_15d
                ),
                latest_activity_at=latest_activity(
                    signal.latest_activity_at, snapshot.latest_activity_at
                ),
                recent_activity_source=snapshot.source,
            )
        )
    return tuple(merged)


def signal_matches_definition(
    signal: CommunitySignal, definition: InterestTagDefinition
) -> bool:
    source_ref_hit = definition.source_ref_match and bool(
        set(signal.source_refs) & set(definition.source_refs)
    )
    if source_ref_hit and has_recommendation_evidence(signal):
        return True
    categories = {normalize_text(item) for item in signal.categories}
    category_keys = {normalize_text(item) for item in definition.category_keys}
    category_match = bool(categories & category_keys)
    if term_hit_count(definition.semantic_keys, signal.semantic_terms) > 0:
        return True
    if community_key_hit_count(
        definition.keyword_keys, signal
    ) and has_recommendation_evidence(signal):
        return True
    keyword_hits = term_hit_count(
        definition.keyword_keys, (*signal.keywords, signal.community)
    )
    return keyword_hits >= 2 or (category_match and keyword_hits > 0)


def signals_for_definition(
    definition: InterestTagDefinition,
    signals: Iterable[CommunitySignal],
) -> list[CommunitySignal]:
    return [s for s in signals if signal_matches_definition(s, definition)]


def community_role(signal: CommunitySignal, policy: RecommendationPolicy) -> str:
    if signal.key in {normalize_text(item) for item in policy.generic_hotspot_keys}:
        return "generic_hotspot"
    return "longtail_vertical"


def build_capability_tags(
    signals: Iterable[CommunitySignal],
    *,
    catalog: InterestTagCatalog | None = None,
) -> tuple[CapabilityTag, ...]:
    active_catalog = catalog or load_interest_tag_catalog()
    signal_list = list(signals)
    tags: list[CapabilityTag] = []
    for definition in active_catalog.tags:
        matched = signals_for_definition(definition, signal_list)
        statuses = [community_status(signal) for signal in matched]
        generic = sum(
            1
            for s in matched
            if community_role(s, active_catalog.policy) == "generic_hotspot"
        )
        sources: set[str] = set()
        for signal in matched:
            sources.update(evidence_sources_for_signal(signal))
        tag_status = (
            READY
            if READY in statuses
            else HISTORICAL_DEPTH
            if HISTORICAL_DEPTH in statuses
            else WATCHING
        )
        tags.append(
            CapabilityTag(
                tag_id=definition.tag_id,
                name=definition.display_name,
                description=definition.short_description,
                group=definition.group,
                status=tag_status,
                user_input_required=False,
                keywords=definition.keyword_keys,
                community_count=len(matched),
                ready_community_count=statuses.count(READY),
                historical_community_count=statuses.count(HISTORICAL_DEPTH),
                watching_community_count=statuses.count(WATCHING),
                generic_community_count=generic,
                longtail_community_count=len(matched) - generic,
                evidence_sources=tuple(sorted(sources)),
                source_refs=definition.source_refs,
            )
        )
    return tuple(tags)
