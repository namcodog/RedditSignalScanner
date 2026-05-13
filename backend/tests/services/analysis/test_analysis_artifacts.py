from __future__ import annotations

from app.services.analysis.analysis_artifacts import (
    apply_report_tier,
    attach_aggregates,
    build_facts_v2_package,
    build_sources_payload,
)


def test_build_facts_v2_package_and_attach_aggregates() -> None:
    payload = build_facts_v2_package(
        topic_label="PayPal",
        topic_profile_id="paypal_v1",
        product_description="帮助卖家看清回款和手续费问题",
        data_lineage={"counts_db": {"posts_current": 12}},
        high_value_pains=[{"topic": "回款延迟与冻结"}],
        brand_pain=[{"name": "PayPal", "mentions": 4}],
        solutions=[{"description": "多平台收款插件配置助手"}],
        opportunities=[{"description": "国际收款账户开通助手"}],
        competitors=[{"name": "Stripe"}],
        ps_ratio=0.12,
        sample_posts_db=[{"id": "p1"}],
        sample_comments_db=[{"id": "c1"}],
        diagnostics={"pipeline": "ok"},
    )
    enriched = attach_aggregates(
        payload,
        aggregates={"communities": [{"name": "r/paypal", "posts": 8}]},
    )

    assert enriched["business_signals"]["ps_ratio"] == 0.12
    assert enriched["aggregates"]["communities"][0]["name"] == "r/paypal"
    assert enriched["diagnostics"]["pipeline"] == "ok"


def test_apply_report_tier_trims_and_resets() -> None:
    insights = {
        "pain_points": [1, 2, 3],
        "competitors": ["a"],
        "opportunities": [1, 2, 3],
        "action_items": [1, 2],
    }

    trimmed, trimmed_actions = apply_report_tier(insights=insights, report_tier="B_trimmed")
    scouting, scouting_actions = apply_report_tier(insights=insights, report_tier="C_scouting")

    assert trimmed["pain_points"] == [1, 2]
    assert trimmed["action_items"] == [1]
    assert trimmed_actions == [1]
    assert scouting == {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
        "action_items": [],
    }
    assert scouting_actions == []


def test_build_sources_payload_wires_optional_contracts() -> None:
    sources = build_sources_payload(
        communities=["r/paypal"],
        posts_analyzed=10,
        comments_analyzed=5,
        data_lineage={"source_range": {"posts": 10}},
        counts_db={"posts_current": 12},
        comments_pipeline_status="ok",
        lookback_days=365,
        cache_hit_rate=0.66,
        ps_ratio=0.0,
        pain_counts_by_community={"r/paypal": 6},
        keywords=["paypal", "payout"],
        fetch_keywords=["paypal"],
        analysis_duration_seconds=84,
        hybrid_posts_used=3,
        hybrid_retrieval_status="ok",
        hybrid_retrieval_reason=None,
        hybrid_retrieval_query="paypal payout",
        reddit_api_calls=2,
        reddit_api_failures=[],
        stale_cache_subreddits=["r/paypal"],
        stale_cache_fallback_subreddits=[],
        collection_warnings=[{"type": "stale"}],
        product_description="帮助卖家看清回款问题",
        mode="market_insight",
        audit_level="lab",
        topic_profile_id="paypal_v1",
        topic_profile={"id": "paypal_v1"},
        communities_detail=[{"name": "r/paypal"}],
        duplicates_summary=[{"deduped": 2}],
        facts_v2_quality={"tier": "A_full"},
        report_tier="A_full",
        dedup_stats={"total_posts": 10},
        post_score_stats={"avg": 0.7},
        noise_pool_stats={"noise": 1},
        seed_source="pool",
        data_source="reddit",
        coverage_status={"status": "ok"},
        trend_degraded=False,
        trend_source=None,
        analysis_diagnostics={"pipeline": "ok"},
        data_readiness={"ready": True},
        remediation_actions=[{"type": "backfill"}],
        facts_v2_package={"schema_version": "2.0"},
        facts_slice={"ps_ratio": 0.0},
        knowledge_graph={"nodes": []},
        analysis_blocked=None,
    )

    assert sources["cache_hit_rate"] == 0.66
    assert sources["facts_v2_package"]["schema_version"] == "2.0"
    assert sources["analysis_diagnostics"]["pipeline"] == "ok"
    assert sources["remediation_actions"][0]["type"] == "backfill"
    assert sources["duplicates_summary"] == [{"deduped": 2}]
