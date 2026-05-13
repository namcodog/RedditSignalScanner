from __future__ import annotations

from app.services.community.community_recommendation_models import (
    CapabilityTag,
    CommunityRecommendation,
    JsonValue,
    PreviewAcceptance,
    RecommendationPreview,
)
from app.services.community.community_recommendation_utils import to_json_value


def tag_payload(tag: CapabilityTag) -> dict[str, JsonValue]:
    return {
        "id": tag.tag_id,
        "display_name": tag.name,
        "short_description": tag.description,
        "group": tag.group,
        "status": tag.status,
        "available_community_count": tag.ready_community_count,
        "debug": {
            "source_refs": to_json_value(tag.source_refs),
            "user_input_required": tag.user_input_required,
            "match_terms": to_json_value(tag.keywords),
            "community_count": tag.community_count,
            "ready_community_count": tag.ready_community_count,
            "historical_community_count": tag.historical_community_count,
            "watching_community_count": tag.watching_community_count,
            "generic_community_count": tag.generic_community_count,
            "longtail_community_count": tag.longtail_community_count,
            "evidence_sources": to_json_value(tag.evidence_sources),
        },
    }


def recommendation_payload(item: CommunityRecommendation) -> dict[str, JsonValue]:
    return {
        "community": item.community,
        "reason": " / ".join(item.reasons),
        "best_for": item.best_for,
        "activity_label": item.activity_label,
        "related_to": to_json_value(item.related_to),
        "evidence_teaser": item.evidence_teaser,
        "debug": {
            "status": item.status,
            "role": item.role,
            "score": item.score,
            "evidence_sources": to_json_value(item.evidence_sources),
            "risk_flags": to_json_value(item.risk_flags),
            "recent_posts_15d": item.recent_posts_15d,
            "latest_activity_at": item.latest_activity_at,
            "historical_posts": item.historical_posts,
            "hotpost_cards": item.hotpost_cards,
            "semantic_observations": item.semantic_observations,
            "semantic_terms": to_json_value(item.semantic_terms),
            "evidence_summary": to_json_value(item.evidence_summary),
            "sample_titles": to_json_value(item.sample_titles),
        },
    }


def acceptance_payload(acceptance: PreviewAcceptance) -> dict[str, JsonValue]:
    return {
        "ready_count": acceptance.ready_count,
        "historical_count": acceptance.historical_count,
        "watching_count": acceptance.watching_count,
        "generic_count": acceptance.generic_count,
        "longtail_count": acceptance.longtail_count,
        "db_writes": acceptance.db_writes,
        "user_input_required": acceptance.user_input_required,
        "passed": acceptance.passed,
        "blockers": to_json_value(acceptance.blockers),
    }


def preview_to_payload(preview: RecommendationPreview) -> dict[str, JsonValue]:
    return {
        "acceptance": acceptance_payload(preview.acceptance),
        "tags": [tag_payload(tag) for tag in preview.tags],
        "recommendations": {
            tag_id: [recommendation_payload(item) for item in items]
            for tag_id, items in preview.recommendations.items()
        },
    }
