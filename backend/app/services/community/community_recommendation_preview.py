from __future__ import annotations

from app.services.community.community_brand_evidence import (
    CommunityBrandEvidence,
    merge_community_brand_evidence,
)
from app.services.community.community_recommendation_builder import build_preview
from app.services.community.community_recommendation_core import (
    build_capability_tags,
    community_status,
    evidence_sources_for_signal,
    merge_activity_snapshots,
)
from app.services.community.community_recommendation_loader import (
    load_community_signals,
)
from app.services.community.community_recommendation_models import (
    CapabilityTag,
    CommunityActivitySnapshot,
    CommunityRecommendation,
    CommunitySignal,
    PreviewAcceptance,
    RecommendationPreview,
)
from app.services.community.community_recommendation_payload import preview_to_payload
from app.services.community.community_recommendation_ranker import (
    build_recommendations_for_tag,
)
from app.services.community.community_recommendation_service import (
    CommunityRecommendationReport,
    build_community_recommendation_report,
    build_community_recommendation_report_from_signals,
)


__all__ = [
    "CapabilityTag",
    "CommunityActivitySnapshot",
    "CommunityBrandEvidence",
    "CommunityRecommendation",
    "CommunityRecommendationReport",
    "CommunitySignal",
    "PreviewAcceptance",
    "RecommendationPreview",
    "build_capability_tags",
    "build_community_recommendation_report",
    "build_community_recommendation_report_from_signals",
    "build_preview",
    "build_recommendations_for_tag",
    "community_status",
    "evidence_sources_for_signal",
    "load_community_signals",
    "merge_activity_snapshots",
    "merge_community_brand_evidence",
    "preview_to_payload",
]
