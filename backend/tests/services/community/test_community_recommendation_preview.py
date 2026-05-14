from __future__ import annotations

from app.services.community.community_recommendation_preview import (
    CapabilityTag,
    CommunitySignal,
    build_capability_tags,
    build_recommendations_for_tag,
)
from app.services.community.interest_tag_catalog import load_interest_tag_catalog


INTERNAL_PUBLIC_TERMS = (
    "Hotpost",
    "community_pool",
    "semantic_observation",
    "semantic ledger",
    "语义账本",
)


def _tag_with_ref(signals: list[CommunitySignal], source_ref: str) -> CapabilityTag:
    return next(
        tag for tag in build_capability_tags(signals) if source_ref in tag.source_refs
    )


def _matched_tag_ids(signals: list[CommunitySignal]) -> list[str]:
    return [tag.tag_id for tag in build_capability_tags(signals) if tag.community_count]


def test_public_reasons_do_not_leak_internal_evidence_terms() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=8,
            historical_posts=40,
            recent_posts_15d=6,
            hotpost_cards=5,
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:agent-incidents")

    recommendations = build_recommendations_for_tag(tag, signals, limit=1)
    public_text = " ".join(recommendations[0].reasons)

    assert not any(
        term.lower() in public_text.lower() for term in INTERNAL_PUBLIC_TERMS
    )


def test_build_capability_tags_from_existing_data_not_user_input() -> None:
    signals = [
        CommunitySignal(
            community="r/shopify",
            keywords=("checkout", "conversion"),
            semantic_observations=5,
            historical_posts=20,
            recent_posts_15d=3,
            hotpost_cards=2,
        ),
        CommunitySignal(
            community="r/amazonfba",
            keywords=("fba", "amazon"),
            semantic_observations=2,
            historical_posts=12,
            recent_posts_15d=0,
            hotpost_cards=0,
        ),
    ]

    tags = build_capability_tags(signals)
    seller_ops = next(
        tag
        for tag in tags
        if "topic_cluster:seller-category-direction" in tag.source_refs
    )

    assert seller_ops.user_input_required is False
    assert seller_ops.status == "ready"
    assert seller_ops.community_count == 2
    assert seller_ops.ready_community_count == 1
    assert seller_ops.historical_community_count == 1
    assert "semantic_observation" in seller_ops.evidence_sources
    assert "community_pool" in seller_ops.evidence_sources


def test_build_capability_tag_marks_historical_depth_without_recent_activity() -> None:
    signals = [
        CommunitySignal(
            community="r/LocalLLaMA",
            keywords=("llm", "agent"),
            semantic_observations=6,
            historical_posts=40,
            recent_posts_15d=0,
            hotpost_cards=0,
        )
    ]

    tags = build_capability_tags(signals)
    tag = next(
        tag for tag in tags if "topic_cluster:agent-incidents" in tag.source_refs
    )

    assert tag.status == "historical_depth"
    assert tag.ready_community_count == 0
    assert tag.historical_community_count == 1


def test_recommendations_include_reasons_evidence_and_longtail_priority() -> None:
    signals = [
        CommunitySignal(
            community="r/OpenAI",
            keywords=("openai", "llm"),
            semantic_observations=10,
            historical_posts=100,
            recent_posts_15d=12,
            hotpost_cards=20,
        ),
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=8,
            historical_posts=40,
            recent_posts_15d=6,
            hotpost_cards=5,
        ),
    ]
    tag = _tag_with_ref(signals, "topic_cluster:agent-incidents")

    recommendations = build_recommendations_for_tag(tag, signals, limit=2)

    assert [item.community for item in recommendations] == ["r/ClaudeCode", "r/OpenAI"]
    assert recommendations[0].role == "longtail_vertical"
    assert recommendations[0].status == "ready"
    assert recommendations[0].reasons
    assert "semantic_observation" in recommendations[0].evidence_sources
    assert "recent_activity_15d" in recommendations[0].evidence_sources
    assert recommendations[1].role == "generic_hotspot"
    assert "generic_hotspot" in recommendations[1].risk_flags


def test_recommendations_use_brand_evidence_without_leaking_internal_source() -> None:
    signals = [
        CommunitySignal(
            community="r/shopify",
            keywords=("checkout", "conversion"),
            semantic_terms=("seller operations",),
            brand_terms=("Shopify", "Etsy"),
            brand_mentions=9,
            brand_count=2,
            recent_posts_15d=2,
            hotpost_cards=1,
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:seller-category-direction")

    recommendation = build_recommendations_for_tag(tag, signals, limit=1)[0]
    public_text = " ".join(recommendation.reasons)

    assert "Shopify" in public_text
    assert "brand_system_evidence" in recommendation.evidence_sources
    assert "brand_system_evidence" not in public_text
    assert "品牌证据" in " / ".join(recommendation.evidence_summary)


def test_tag_matching_does_not_use_loose_substrings_or_single_cross_domain_terms() -> (
    None
):
    signals = [
        CommunitySignal(
            community="r/fulfillmentbyamazon",
            keywords=("fba", "amazon"),
            hotpost_cards=28,
        ),
        CommunitySignal(
            community="r/google_ads",
            keywords=("Gemini and Claude were mentioned once",),
            hotpost_cards=9,
        ),
    ]

    tags = build_capability_tags(signals)

    assert _matched_tag_ids(signals) == [
        tag.tag_id
        for tag in load_interest_tag_catalog().tags
        if "topic_cluster:seller-category-direction" in tag.source_refs
    ]


def test_tag_matching_can_use_community_key_when_evidence_exists() -> None:
    signals = [
        CommunitySignal(
            community="r/FulfillmentByAmazon",
            recent_posts_15d=1,
            hotpost_cards=3,
        )
    ]

    tags = build_capability_tags(signals)

    assert _matched_tag_ids(signals) == [
        tag.tag_id
        for tag in load_interest_tag_catalog().tags
        if "topic_cluster:seller-category-direction" in tag.source_refs
    ]
