from __future__ import annotations

from typing import Iterable

from app.services.community.community_recommendation_core import build_capability_tags
from app.services.community.community_recommendation_models import (
    HISTORICAL_DEPTH,
    READY,
    WATCHING,
    CommunityRecommendation,
    CommunitySignal,
    PreviewAcceptance,
    RecommendationPreview,
)
from app.services.community.community_recommendation_ranker import (
    build_recommendations_for_tag,
)
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    load_interest_tag_catalog,
)
from app.services.hotpost.hotpost_community_activity import normalize_community_key


def build_preview(
    signals: Iterable[CommunitySignal],
    *,
    tag_limit: int = 10,
    community_limit: int = 20,
    catalog: InterestTagCatalog | None = None,
) -> RecommendationPreview:
    active_catalog = catalog or load_interest_tag_catalog()
    signal_list = list(signals)
    tags = build_capability_tags(signal_list, catalog=active_catalog)[
        : max(1, tag_limit)
    ]
    recommendations = {
        tag.tag_id: build_recommendations_for_tag(
            tag,
            signal_list,
            limit=community_limit,
            catalog=active_catalog,
        )
        for tag in tags
    }
    all_items = [item for items in recommendations.values() for item in items]
    acceptance_items = _dedupe_recommendations_by_community(all_items)
    ready_count = sum(1 for item in acceptance_items if item.status == READY)
    historical_count = sum(
        1 for item in acceptance_items if item.status == HISTORICAL_DEPTH
    )
    watching_count = sum(1 for item in acceptance_items if item.status == WATCHING)
    generic_count = sum(
        1 for item in acceptance_items if item.role == "generic_hotspot"
    )
    blockers: list[str] = []
    if ready_count == 0:
        blockers.append("no_ready_recommendations")
    if not any(item.semantic_terms for item in acceptance_items):
        blockers.append("no_semantic_terms")
    if not acceptance_items:
        blockers.append("no_recommendations")
    return RecommendationPreview(
        tags=tags,
        recommendations=recommendations,
        acceptance=PreviewAcceptance(
            ready_count=ready_count,
            historical_count=historical_count,
            watching_count=watching_count,
            generic_count=generic_count,
            longtail_count=len(acceptance_items) - generic_count,
            passed=not blockers,
            blockers=tuple(blockers),
        ),
    )


def _dedupe_recommendations_by_community(
    items: list[CommunityRecommendation],
) -> list[CommunityRecommendation]:
    by_key: dict[str, CommunityRecommendation] = {}
    for item in items:
        key = normalize_community_key(item.community) or item.community.lower()
        by_key.setdefault(key, item)
    return list(by_key.values())
