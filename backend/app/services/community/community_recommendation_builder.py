from __future__ import annotations

from typing import Iterable

from app.services.community.community_recommendation_core import build_capability_tags
from app.services.community.community_recommendation_models import (
    HISTORICAL_DEPTH,
    READY,
    WATCHING,
    CommunitySignal,
    PreviewAcceptance,
    RecommendationPreview,
)
from app.services.community.community_recommendation_ranker import build_recommendations_for_tag
from app.services.community.interest_tag_catalog import InterestTagCatalog, load_interest_tag_catalog


def build_preview(
    signals: Iterable[CommunitySignal],
    *,
    tag_limit: int = 10,
    community_limit: int = 20,
    catalog: InterestTagCatalog | None = None,
) -> RecommendationPreview:
    active_catalog = catalog or load_interest_tag_catalog()
    signal_list = list(signals)
    tags = build_capability_tags(signal_list, catalog=active_catalog)[: max(1, tag_limit)]
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
    ready_count = sum(1 for item in all_items if item.status == READY)
    historical_count = sum(1 for item in all_items if item.status == HISTORICAL_DEPTH)
    watching_count = sum(1 for item in all_items if item.status == WATCHING)
    generic_count = sum(1 for item in all_items if item.role == "generic_hotspot")
    blockers: list[str] = []
    if ready_count == 0:
        blockers.append("no_ready_recommendations")
    if not any(item.semantic_terms for item in all_items):
        blockers.append("no_semantic_terms")
    if not all_items:
        blockers.append("no_recommendations")
    return RecommendationPreview(
        tags=tags,
        recommendations=recommendations,
        acceptance=PreviewAcceptance(
            ready_count=ready_count,
            historical_count=historical_count,
            watching_count=watching_count,
            generic_count=generic_count,
            longtail_count=len(all_items) - generic_count,
            passed=not blockers,
            blockers=tuple(blockers),
        ),
    )
