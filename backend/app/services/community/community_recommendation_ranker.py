from __future__ import annotations

from typing import Iterable, cast

from app.services.community.community_recommendation_core import (
    community_role,
    community_status,
    evidence_sources_for_signal,
    signals_for_definition,
)
from app.services.community.community_recommendation_models import (
    HISTORICAL_DEPTH,
    READY,
    WATCHING,
    CapabilityTag,
    CommunityRecommendation,
    CommunitySignal,
    PreviewAcceptance,
    RecommendationPreview,
)
from app.services.community.community_recommendation_text import (
    evidence_summary,
    evidence_teaser,
    public_reasons,
    public_terms,
)
from app.services.community.community_recommendation_utils import (
    dedupe,
    normalize_text,
    tokenize,
)
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    InterestTagDefinition,
    RecommendationPolicy,
    load_interest_tag_catalog,
)


def community_score(signal: CommunitySignal, policy: RecommendationPolicy) -> float:
    weights = cast(dict[str, float], policy.score_weights)
    score = (
        policy.status_bonus[community_status(signal)]
        + min(
            signal.recent_posts_15d * weights["recent_posts_15d_weight"],
            weights["recent_posts_15d_cap"],
        )
        + min(
            signal.historical_posts * weights["historical_posts_weight"],
            weights["historical_posts_cap"],
        )
        + min(
            signal.semantic_observations * weights["semantic_observations_weight"],
            weights["semantic_observations_cap"],
        )
        + min(
            signal.hotpost_cards * weights["hotpost_cards_weight"],
            weights["hotpost_cards_cap"],
        )
        + min(
            signal.content_labels * weights["content_labels_weight"],
            weights["content_labels_cap"],
        )
        + min(
            signal.content_entities * weights["content_entities_weight"],
            weights["content_entities_cap"],
        )
        + min(
            max(signal.quality_score, 0.0) * weights["quality_score_weight"],
            weights["quality_score_cap"],
        )
    )
    if community_role(signal, policy) == "generic_hotspot":
        score *= weights["generic_multiplier"]
    return float(round(score, 4))


def semantic_terms_for_definition(
    signal: CommunitySignal,
    definition: InterestTagDefinition,
) -> tuple[str, ...]:
    terms = list(signal.semantic_terms)
    terms.extend(signal.content_label_terms)
    terms.extend(signal.content_entity_terms)
    if terms:
        return cast(tuple[str, ...], dedupe(terms, limit=5))
    categories = {normalize_text(item) for item in signal.categories}
    category_keys = {normalize_text(item) for item in definition.category_keys}
    terms.extend(sorted(categories & category_keys))
    tokens = tokenize(" ".join((*signal.keywords, signal.community)))
    for keyword in (*definition.semantic_keys, *definition.keyword_keys):
        key = normalize_text(keyword)
        if key in tokens:
            terms.append(key)
    return cast(tuple[str, ...], dedupe(terms, limit=5))


def risk_flags(
    signal: CommunitySignal, policy: RecommendationPolicy
) -> tuple[str, ...]:
    flags: list[str] = []
    if community_role(signal, policy) == "generic_hotspot":
        flags.append("generic_hotspot")
    if community_status(signal) == HISTORICAL_DEPTH:
        flags.append("stale_recent_activity")
    if community_status(signal) == WATCHING:
        flags.append("needs_more_evidence")
    return tuple(flags)


def build_recommendations_for_tag(
    tag: CapabilityTag,
    signals: Iterable[CommunitySignal],
    *,
    limit: int = 20,
    generic_cap_ratio: float | None = None,
    catalog: InterestTagCatalog | None = None,
) -> tuple[CommunityRecommendation, ...]:
    active_catalog = catalog or load_interest_tag_catalog()
    policy = active_catalog.policy
    definition = active_catalog.definition_for(tag.tag_id)
    rows: list[CommunityRecommendation] = []
    for signal in signals_for_definition(definition, signals):
        terms = semantic_terms_for_definition(signal, definition)
        display_terms = public_terms(terms, tag.name)
        status = community_status(signal)
        role = community_role(signal, policy)
        rows.append(
            CommunityRecommendation(
                community=signal.community,
                status=status,
                role=role,
                score=community_score(signal, policy),
                reasons=public_reasons(signal, policy, display_terms),
                evidence_sources=evidence_sources_for_signal(signal),
                risk_flags=risk_flags(signal, policy),
                recent_posts_15d=signal.recent_posts_15d,
                latest_activity_at=signal.latest_activity_at,
                historical_posts=signal.historical_posts,
                hotpost_cards=signal.hotpost_cards,
                semantic_observations=signal.semantic_observations,
                brand_terms=signal.brand_terms,
                brand_mentions=signal.brand_mentions,
                brand_count=signal.brand_count,
                semantic_terms=terms,
                evidence_summary=evidence_summary(signal, terms, policy),
                sample_titles=signal.sample_titles,
                best_for=policy.role_labels.get(role, role),
                activity_label=policy.activity_labels.get(status, status),
                related_to=display_terms,
                evidence_teaser=evidence_teaser(signal, policy),
            )
        )
    rows.sort(
        key=lambda r: (
            {READY: 2, HISTORICAL_DEPTH: 1, WATCHING: 0}[r.status],
            r.role == "longtail_vertical",
            r.score,
        ),
        reverse=True,
    )
    return tuple(_apply_generic_cap(rows, policy, limit, generic_cap_ratio))


def _apply_generic_cap(
    rows: list[CommunityRecommendation],
    policy: RecommendationPolicy,
    limit: int,
    cap_ratio: float | None,
) -> list[CommunityRecommendation]:
    generic_limit = max(
        0,
        int(
            max(0.0, cap_ratio if cap_ratio is not None else policy.generic_cap_ratio)
            * max(1, limit)
        ),
    )
    if generic_limit == 0 and any(row.role == "generic_hotspot" for row in rows):
        generic_limit = 1
    used = 0
    capped: list[CommunityRecommendation] = []
    for row in rows:
        if row.role == "generic_hotspot":
            if used >= generic_limit:
                continue
            used += 1
        capped.append(row)
    return capped[: max(1, limit)]
