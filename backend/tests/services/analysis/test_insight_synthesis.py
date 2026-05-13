from __future__ import annotations

from app.services.analysis.insight_synthesis import (
    build_opportunities_payload,
    build_pain_points_payload,
    finalize_insights_summary,
)
from app.services.analysis.signal_extraction import OpportunitySignal, PainPointSignal


def test_build_pain_points_payload_prefers_translated_cjk_and_filters_examples() -> None:
    pain_signals = [
        PainPointSignal(
            description="payout delayed after shipping",
            frequency=6,
            sentiment=-0.7,
            keywords=["delay", "shipping"],
            source_posts=["p1"],
            relevance=0.82,
        )
    ]

    payload = build_pain_points_payload(
        pain_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {
                "post_id": source_posts[0],
                "title": anchor_text,
                "url": "https://www.reddit.com/r/stripe/comments/demo/payout-delay/",
            }
        ],
        build_user_examples=lambda _source_posts, _anchor_text: [
            "English-only fallback should be filtered",
            "卖家反馈发货后依然迟迟不到账。",
        ],
        translate_pain_signal=lambda raw_description, _source_examples: {
            "description": "发货后回款迟迟不到账",
            "user_examples": [
                f"围绕{raw_description}，卖家连续吐槽到账拖延。",
                "Plain English text",
            ],
        },
        classify_pain_severity=lambda frequency, sentiment: "high"
        if frequency >= 5 and sentiment < -0.5
        else "medium",
    )

    assert payload[0]["description"] == "发货后回款迟迟不到账"
    assert payload[0]["severity"] == "high"
    assert payload[0]["user_examples"] == ["围绕payout delayed after shipping，卖家连续吐槽到账拖延。"]


def test_build_pain_points_payload_keeps_scaffold_when_translation_stays_english() -> None:
    pain_signals = [
        PainPointSignal(
            description="need to pay the supplier upfront before payouts arrive",
            frequency=4,
            sentiment=-0.6,
            keywords=["supplier", "payout"],
            source_posts=["p9"],
            relevance=0.71,
        )
    ]

    payload = build_pain_points_payload(
        pain_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {
                "post_id": source_posts[0],
                "title": "need to pay the supplier upfront before payouts arrive",
                "url": "https://www.reddit.com/r/dropshipping/comments/demo/cashflow/",
            }
        ],
        build_user_examples=lambda _source_posts, _anchor_text: [],
        translate_pain_signal=lambda raw_description, _source_examples: {
            "description": raw_description,
            "user_examples": [],
        },
        classify_pain_severity=lambda _frequency, _sentiment: "high",
    )

    assert len(payload) == 1
    assert payload[0]["description"] == "回款慢、手续费高，现金周转经常被卡住"
    assert payload[0]["user_examples"] == [f"围绕「{payload[0]['description']}」的抱怨在本轮样本里反复出现。"]


def test_build_opportunities_payload_links_cluster_and_uses_ledger_ready_copy() -> None:
    opportunity_signals = [
        OpportunitySignal(
            description="bank account onboarding for international payments",
            demand_score=0.81,
            unmet_need="manual bank onboarding",
            potential_users=1552,
            source_posts=["p2"],
            relevance=0.74,
            keywords=["开户卡住", "手续费高"],
        )
    ]

    payload = build_opportunities_payload(
        opportunity_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {
                "post_id": source_posts[0],
                "title": anchor_text,
                "url": "https://www.reddit.com/r/paypal/comments/demo/account-onboarding/",
            }
        ],
        translate_opportunity_signal=lambda _raw_description, _source_examples: {
            "description": "国际收款账户开通助手",
            "linked_pain_cluster": "国际收款开通受阻",
            "key_insights": ["排查银行国际收款开通状态", "缩短跨境到账时间"],
        },
        clusters=[
            {"topic": "国际收款开通受阻"},
            {"topic": "回款延迟与冻结"},
        ],
        fallback_channels=["r/paypal", "r/stripe"],
        select_opportunity_channels=lambda _source_examples, fallback_channels: list(
            fallback_channels[:2]
        ),
    )

    assert payload[0]["description"] == "国际收款账户开通助手"
    assert payload[0]["linked_pain_cluster"] == "国际收款开通受阻"
    assert payload[0]["top_channels"] == ["r/paypal", "r/stripe"]
    assert payload[0]["key_insights"][0] == "国际收款开通受阻"


def test_build_opportunities_payload_keeps_cjk_scaffold_when_translation_stays_english() -> None:
    opportunity_signals = [
        OpportunitySignal(
            description="subscription cleanup helper for monthly savings",
            demand_score=0.64,
            unmet_need="manual subscription review",
            potential_users=1320,
            source_posts=["p8"],
            relevance=0.67,
            keywords=["subscription", "save money"],
        )
    ]

    payload = build_opportunities_payload(
        opportunity_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {
                "post_id": source_posts[0],
                "title": anchor_text,
                "url": "https://www.reddit.com/r/Frugal/comments/demo/subscription-cleanup/",
            }
        ],
        translate_opportunity_signal=lambda raw_description, _source_examples: {
            "description": raw_description,
            "linked_pain_cluster": "",
            "key_insights": [],
        },
        clusters=[],
        fallback_channels=["r/Frugal"],
        select_opportunity_channels=lambda _source_examples, fallback_channels: list(fallback_channels),
    )

    assert len(payload) == 1
    assert payload[0]["description"] == "订阅账单盘点与省钱提醒助手"


def test_build_pain_points_payload_turns_edc_bulk_noise_into_cjk_business_copy() -> None:
    pain_signals = [
        PainPointSignal(
            description="I love EDC but hate being bulked down",
            frequency=5,
            sentiment=-0.7,
            keywords=["edc", "carry", "bulk"],
            source_posts=["p10"],
            relevance=0.72,
        )
    ]

    payload = build_pain_points_payload(
        pain_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {"post_id": source_posts[0], "title": anchor_text, "url": "https://www.reddit.com/r/EDC/comments/demo/"}
        ],
        build_user_examples=lambda _source_posts, _anchor_text: [],
        translate_pain_signal=lambda raw_description, _source_examples: {
            "description": raw_description,
            "user_examples": [],
        },
        classify_pain_severity=lambda _frequency, _sentiment: "high",
    )

    assert payload[0]["description"] == "随身小物一多，口袋发鼓、分类混乱，拿取很不顺手"


def test_build_opportunities_payload_turns_ai_workflow_noise_into_cjk_business_copy() -> None:
    opportunity_signals = [
        OpportunitySignal(
            description="internal tool to keep workflow progress visible",
            demand_score=0.61,
            unmet_need="manual status sync",
            potential_users=980,
            source_posts=["p11"],
            relevance=0.65,
            keywords=["workflow", "progress", "knowledge"],
        )
    ]

    payload = build_opportunities_payload(
        opportunity_signals,
        build_example_posts=lambda source_posts, anchor_text, include_title=False: [
            {"post_id": source_posts[0], "title": anchor_text, "url": "https://www.reddit.com/r/ChatGPT/comments/demo/"}
        ],
        translate_opportunity_signal=lambda raw_description, _source_examples: {
            "description": raw_description,
            "linked_pain_cluster": "",
            "key_insights": [],
        },
        clusters=[],
        fallback_channels=["r/ChatGPT"],
        select_opportunity_channels=lambda _source_examples, fallback_channels: list(fallback_channels),
    )

    assert payload[0]["description"] == "团队协作进度与知识归档助手"


def test_finalize_insights_summary_builds_action_driver_and_battlefield_views() -> None:
    summary = finalize_insights_summary(
        insights={
            "pain_points": [{"description": "回款延迟与冻结", "frequency": 6}],
            "opportunities": [{"description": "国际收款账户开通助手"}],
        },
        communities_detail=[{"name": "r/paypal", "mentions": 8}],
        pain_counts_by_community={"r/paypal": 6},
        build_action_reports=lambda insights: [
            {
                "problem_definition": insights["opportunities"][0]["description"],
                "evidence_chain": [],
            }
        ],
        summarize_entities=lambda _insights: {
            "channels": [
                {"name": "r/paypal", "mentions": 8},
                {"name": "r/stripe", "mentions": 5},
            ]
        },
        summarize_entities_fallback=lambda _insights: {"channels": []},
        build_battlefield_profiles=lambda communities_detail, pain_points, pain_counts, limit: [
            {
                "community": communities_detail[0]["name"],
                "top_pain": pain_points[0]["description"],
                "pain_mentions": pain_counts[communities_detail[0]["name"]],
                "limit": limit,
            }
        ],
        build_top_drivers=lambda pain_points, action_items, limit: [
            {
                "label": pain_points[0]["description"],
                "action": action_items[0]["problem_definition"],
                "limit": limit,
            }
        ],
    )

    assert summary.insights["action_items"][0]["problem_definition"] == "国际收款账户开通助手"
    assert summary.channel_breakdown[0]["name"] == "r/paypal"
    assert summary.top_communities == ["r/paypal"]
    assert summary.insights["top_communities"] == ["r/paypal"]
    assert summary.battlefield_profiles[0]["community"] == "r/paypal"
    assert summary.top_drivers[0]["action"] == "国际收款账户开通助手"
    assert summary.insights["drivers"][0]["action"] == "国际收款账户开通助手"
