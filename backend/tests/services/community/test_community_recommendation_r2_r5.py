from __future__ import annotations

from app.services.community.community_recommendation_preview import (
    CommunityActivitySnapshot,
    CommunitySignal,
    build_capability_tags,
    build_preview,
    build_recommendations_for_tag,
    merge_activity_snapshots,
)


def _tag_with_ref(signals: list[CommunitySignal], source_ref: str):
    return next(
        tag
        for tag in build_capability_tags(signals)
        if source_ref in tag.source_refs
    )


def test_r2_activity_snapshot_promotes_current_evidence_to_ready() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=3,
            historical_posts=20,
            recent_posts_15d=0,
        )
    ]
    snapshots = [
        CommunityActivitySnapshot(
            community="r/ClaudeCode",
            recent_posts_15d=7,
            latest_activity_at="2026-05-07T10:00:00+08:00",
            source="live_probe",
        )
    ]

    merged = merge_activity_snapshots(signals, snapshots)
    tag = _tag_with_ref(list(merged), "topic_cluster:agent-incidents")
    recommendations = build_recommendations_for_tag(tag, merged, limit=1)

    assert tag.status == "ready"
    assert recommendations[0].status == "ready"
    assert recommendations[0].latest_activity_at == "2026-05-07T10:00:00+08:00"
    assert "recent_activity_15d" in recommendations[0].evidence_sources


def test_r3_recommendations_carry_semantic_terms_and_evidence_summary() -> None:
    signals = [
        CommunitySignal(
            community="r/EtsySellers",
            keywords=("etsy", "conversion"),
            semantic_observations=4,
            semantic_terms=("conversion friction", "product photos"),
            historical_posts=30,
            recent_posts_15d=2,
            hotpost_cards=3,
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:seller-category-direction")

    recommendations = build_recommendations_for_tag(tag, signals, limit=1)

    assert recommendations[0].semantic_terms == ("conversion friction", "product photos")
    assert any("语义证据" in item for item in recommendations[0].evidence_summary)
    assert any("product photos" in item for item in recommendations[0].evidence_summary)


def test_r4_generic_hotspots_are_capped_and_longtail_is_prioritized() -> None:
    signals = [
        CommunitySignal(
            community="r/OpenAI",
            keywords=("openai", "llm"),
            semantic_observations=20,
            historical_posts=120,
            recent_posts_15d=9,
            hotpost_cards=20,
        ),
        CommunitySignal(
            community="r/ChatGPT",
            keywords=("openai", "llm"),
            semantic_observations=18,
            historical_posts=100,
            recent_posts_15d=8,
            hotpost_cards=10,
        ),
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=5,
            historical_posts=20,
            recent_posts_15d=3,
            hotpost_cards=5,
        ),
        CommunitySignal(
            community="r/LocalLLaMA",
            keywords=("llm", "agent"),
            semantic_observations=4,
            historical_posts=18,
            recent_posts_15d=2,
            hotpost_cards=3,
        ),
    ]
    tag = _tag_with_ref(signals, "topic_cluster:agent-incidents")

    recommendations = build_recommendations_for_tag(tag, signals, limit=4)

    assert [item.community for item in recommendations[:2]] == ["r/ClaudeCode", "r/LocalLLaMA"]
    assert sum(1 for item in recommendations if item.role == "generic_hotspot") == 1
    assert tag.generic_community_count == 2
    assert tag.longtail_community_count == 2


def test_r5_preview_has_backend_acceptance_summary() -> None:
    signals = [
        CommunitySignal(
            community="r/Shopify",
            keywords=("shopify", "conversion"),
            semantic_observations=4,
            semantic_terms=("checkout conversion",),
            historical_posts=20,
            recent_posts_15d=5,
            hotpost_cards=2,
        ),
        CommunitySignal(
            community="r/EtsySellers",
            keywords=("etsy", "product photos"),
            semantic_observations=2,
            semantic_terms=("product photos",),
            historical_posts=10,
            recent_posts_15d=1,
        ),
    ]

    preview = build_preview(signals, tag_limit=10, community_limit=5)

    assert preview.acceptance.db_writes is False
    assert preview.acceptance.user_input_required is False
    assert preview.acceptance.ready_count == 2
    assert preview.acceptance.longtail_count == 2
    assert preview.acceptance.passed is True
