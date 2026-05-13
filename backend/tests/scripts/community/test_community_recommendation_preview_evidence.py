from __future__ import annotations

from app.services.community.community_recommendation_preview import (
    CapabilityTag,
    CommunityRecommendation,
    PreviewAcceptance,
    RecommendationPreview,
)
from scripts.community.community_recommendation_preview import render_markdown


def test_render_markdown_shows_public_evidence_teaser_column() -> None:
    preview = RecommendationPreview(
        tags=(
            CapabilityTag(
                tag_id="fixture_tag",
                name="Fixture Tag",
                description="Fixture description.",
                group="Fixture Group",
                status="ready",
                user_input_required=False,
                keywords=("agent", "workflow"),
                community_count=1,
                ready_community_count=1,
                historical_community_count=0,
                watching_community_count=0,
                generic_community_count=0,
                longtail_community_count=1,
                evidence_sources=("semantic_terms",),
            ),
        ),
        recommendations={
            "fixture_tag": (
                CommunityRecommendation(
                    community="r/ClaudeCode",
                    status="ready",
                    role="longtail_vertical",
                    score=120.0,
                    reasons=("15 天内 4 条相关讨论；主题集中在 agent workflow。",),
                    evidence_sources=("semantic_terms",),
                    risk_flags=(),
                    recent_posts_15d=4,
                    historical_posts=20,
                    hotpost_cards=5,
                    semantic_observations=8,
                    semantic_terms=("agent workflow",),
                    evidence_summary=("代表讨论：团队把 Claude 接进日常开发流程",),
                    sample_titles=("团队把 Claude 接进日常开发流程",),
                    evidence_teaser="代表讨论：团队把 Claude 接进日常开发流程",
                    latest_activity_at="2026-05-07T10:00:00+08:00",
                ),
            )
        },
        acceptance=PreviewAcceptance(
            ready_count=1,
            historical_count=0,
            watching_count=0,
            generic_count=0,
            longtail_count=1,
            passed=True,
            blockers=(),
        ),
    )

    markdown = render_markdown(preview)
    public_section = markdown.split("## Debug Evidence", maxsplit=1)[0]

    assert "| Community | Activity | Best For | Evidence | Score | Reason |" in public_section
    assert "代表讨论：团队把 Claude 接进日常开发流程" in public_section
