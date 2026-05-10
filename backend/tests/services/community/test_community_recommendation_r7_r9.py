from __future__ import annotations

from app.services.community.community_recommendation_audit import (
    build_recommendation_audit,
    render_audit_markdown,
)
from app.services.community.community_recommendation_preview import (
    CommunitySignal,
    build_capability_tags,
    build_preview,
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


def _tag_with_ref(signals: list[CommunitySignal], source_ref: str):
    return next(
        tag
        for tag in build_capability_tags(signals)
        if source_ref in tag.source_refs
    )


def _configured_name(source_ref: str) -> str:
    return next(
        tag.display_name
        for tag in load_interest_tag_catalog().tags
        if source_ref in tag.source_refs
    )


def test_r7_public_reason_uses_specific_evidence_not_plain_templates() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=5,
            semantic_terms=("agent workflow", "developer automation"),
            historical_posts=20,
            recent_posts_15d=3,
            hotpost_cards=5,
            sample_titles=("团队开始把 Claude 接进日常开发流程",),
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:agent-incidents")

    recommendation = build_recommendations_for_tag(tag, signals, limit=1)[0]
    reason = " ".join(recommendation.reasons)

    assert "15 天内 3 条" in reason
    assert "agent workflow" in reason
    assert "5 条高价值信号" in reason
    assert "近期有真实讨论，适合观察当前问题和需求。" not in reason
    assert not any(term.lower() in reason.lower() for term in INTERNAL_PUBLIC_TERMS)


def test_r7_public_reason_hides_backend_category_terms() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            recent_posts_15d=2,
            hotpost_cards=2,
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:agent-incidents")

    recommendation = build_recommendations_for_tag(tag, signals, limit=1)[0]
    public_text = " ".join((*recommendation.reasons, *recommendation.related_to))

    assert "ai_workflow" not in public_text.lower()
    assert recommendation.related_to
    assert all("_" not in item for item in recommendation.related_to)


def test_r8_builds_tag_community_audit_rows_for_review() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_observations=5,
            semantic_terms=("agent workflow",),
            historical_posts=20,
            recent_posts_15d=3,
            hotpost_cards=5,
        ),
        CommunitySignal(
            community="r/automation",
            keywords=("agent", "workflow"),
            recent_posts_15d=0,
            hotpost_cards=0,
        ),
    ]
    preview = build_preview(signals, tag_limit=10, community_limit=5)

    audit = build_recommendation_audit(preview)
    markdown = render_audit_markdown(audit)

    assert audit.row_count == 2
    assert _configured_name("topic_cluster:agent-incidents") in markdown
    assert "r/ClaudeCode" in markdown
    assert "推荐通过" in markdown
    assert "补证据" in markdown


def test_r9_label_and_entity_terms_increase_semantic_evidence_density() -> None:
    signals = [
        CommunitySignal(
            community="r/Shopify",
            keywords=("shopify", "conversion"),
            content_labels=2,
            content_entities=1,
            content_label_terms=("checkout friction",),
            content_entity_terms=("Shopify",),
            historical_posts=8,
            recent_posts_15d=2,
        )
    ]
    tag = _tag_with_ref(signals, "topic_cluster:seller-category-direction")

    recommendation = build_recommendations_for_tag(tag, signals, limit=1)[0]

    assert recommendation.semantic_terms == ("checkout friction", "Shopify")
    assert any("checkout friction" in item for item in recommendation.evidence_summary)
    assert build_preview(signals, tag_limit=10, community_limit=5).acceptance.passed is True
