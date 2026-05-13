from __future__ import annotations

from app.services.community.community_recommendation_preview import (
    CapabilityTag,
    CommunityRecommendation,
    PreviewAcceptance,
    RecommendationPreview,
)
from scripts.community.community_recommendation_preview import render_markdown


INTERNAL_PUBLIC_TERMS = (
    "Hotpost",
    "community_pool",
    "semantic_observation",
    "semantic ledger",
    "语义账本",
)


def test_render_markdown_shows_system_generated_tags_and_evidence() -> None:
    preview = RecommendationPreview(
        tags=(
            CapabilityTag(
                tag_id="fixture_tag",
                name="Fixture Tag",
                description="Fixture description.",
                group="Fixture Group",
                status="historical_depth",
                user_input_required=False,
                keywords=("shopify", "amazon"),
                community_count=1,
                ready_community_count=0,
                historical_community_count=1,
                watching_community_count=0,
                generic_community_count=0,
                longtail_community_count=1,
                evidence_sources=("community_pool", "historical_posts"),
            ),
        ),
        recommendations={
            "fixture_tag": (
                CommunityRecommendation(
                    community="r/shopify",
                    status="historical_depth",
                    role="longtail_vertical",
                    score=72.5,
                    reasons=("旧 DB 有历史讨论深度，但近期活跃待补证据",),
                    evidence_sources=("community_pool", "historical_posts"),
                    risk_flags=("stale_recent_activity",),
                    recent_posts_15d=0,
                    historical_posts=20,
                    hotpost_cards=0,
                    semantic_observations=0,
                    semantic_terms=(),
                    evidence_summary=("旧 DB 有历史讨论深度，但近期活跃待补证据",),
                    latest_activity_at=None,
                ),
            )
        },
        acceptance=PreviewAcceptance(
            ready_count=0,
            historical_count=1,
            watching_count=0,
            generic_count=0,
            longtail_count=1,
            passed=False,
            blockers=("no_ready_recommendations",),
        ),
    )

    markdown = render_markdown(preview)

    assert "# Community Recommendation Preview" in markdown
    assert "- user_input_required: `false`" in markdown
    assert "## Fixture Tag" in markdown
    assert "r/shopify" in markdown
    assert "旧 DB 有历史讨论深度" in markdown
    assert "stale_recent_activity" in markdown
    assert "Acceptance" in markdown
    assert "no_ready_recommendations" in markdown


def test_render_markdown_public_section_hides_internal_evidence_terms() -> None:
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
                evidence_sources=(
                    "community_pool",
                    "semantic_observation",
                    "hotpost_published_cards",
                ),
            ),
        ),
        recommendations={
            "fixture_tag": (
                CommunityRecommendation(
                    community="r/ClaudeCode",
                    status="ready",
                    role="longtail_vertical",
                    score=120.0,
                    reasons=("近期有真实讨论，适合观察当前问题和需求。",),
                    evidence_sources=(
                        "community_pool",
                        "semantic_observation",
                        "hotpost_published_cards",
                    ),
                    risk_flags=(),
                    recent_posts_15d=4,
                    historical_posts=20,
                    hotpost_cards=5,
                    semantic_observations=8,
                    semantic_terms=("agent", "workflow"),
                    evidence_summary=("Hotpost 探测：已产出 5 张卡",),
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

    assert not any(term.lower() in public_section.lower() for term in INTERNAL_PUBLIC_TERMS)
