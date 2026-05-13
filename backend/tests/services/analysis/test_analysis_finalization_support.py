from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.analysis.analysis_finalization_support import (
    apply_quality_gate_to_insights,
    apply_trend_summary_if_needed,
    calculate_confidence_score,
    finalize_analysis_outputs,
)
from app.services.analysis.analysis_rendering import (
    AnalysisReportRenderBundle,
    StructuredReportRenderResult,
)


def test_calculate_confidence_score_clamps_and_rounds() -> None:
    score = calculate_confidence_score(
        cache_hit_rate=1.0,
        posts_analyzed=200,
        communities_found=20,
        pain_points_count=10,
        competitors_count=5,
        opportunities_count=5,
    )

    assert score == 1.0


def test_apply_quality_gate_to_insights_respects_insufficient_sample_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis.analysis_finalization_support.quality_check_facts_v2",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            tier="A_full",
            flags=["good"],
            metrics={"coverage_tier": "partial"},
        ),
    )

    artifacts = apply_quality_gate_to_insights(
        facts_v2_package={"schema_version": "2.0"},
        topic_profile=None,
        analysis_blocked_reason="insufficient_samples",
        deduped_posts_count=42,
        min_posts=1500,
        lookback_days=365,
        insights={
            "pain_points": [{"description": "p1"}],
            "competitors": [{"name": "c1"}],
            "opportunities": [{"description": "o1"}],
            "action_items": [{"title": "a1"}],
        },
    )

    assert artifacts.report_tier == "C_scouting"
    assert artifacts.facts_v2_quality["tier"] == "C_scouting"
    assert "insufficient_samples" in artifacts.facts_v2_quality["flags"]
    assert artifacts.insights == {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
        "action_items": [],
    }
    assert artifacts.action_reports == []


def test_apply_trend_summary_if_needed_appends_coverage_reason() -> None:
    insights, trend_degraded, trend_sources = apply_trend_summary_if_needed(
        insights={"pain_points": [], "competitors": [], "opportunities": [], "action_items": []},
        report_tier="A_full",
        facts_v2_quality={"metrics": {"coverage_tier": "partial"}},
        trend_series=[{"period": "2026-01", "post_count": 12}],
        trend_degraded=False,
        trend_sources=[],
    )

    assert trend_degraded is True
    assert "coverage_partial" in trend_sources
    assert "trend_summary" in insights


@pytest.mark.asyncio
async def test_finalize_analysis_outputs_wires_sources_render_and_confidence() -> None:
    async def _fake_check_trend() -> tuple[bool, list[str]]:
        return False, []

    async def _fake_render(**_kwargs: object) -> AnalysisReportRenderBundle:
        return AnalysisReportRenderBundle(
            report_html="<html>ok</html>",
            structured_render=StructuredReportRenderResult(
                report={
                    "pain_points": [
                        {
                            "title": "p1",
                            "evidence_chain": [
                                {
                                    "title": "pain evidence",
                                    "url": "https://www.reddit.com/r/paypal/comments/demo1/pain/",
                                    "note": "r/paypal",
                                }
                            ],
                        }
                    ],
                    "opportunities": [
                        {
                            "title": "o1",
                            "evidence_chain": [
                                {
                                    "title": "opp evidence",
                                    "url": "https://www.reddit.com/r/paypal/comments/demo2/opportunity/",
                                    "note": "r/paypal",
                                }
                            ],
                        }
                    ],
                    "target_communities": ["r/paypal"],
                },
                status="completed",
                reason=None,
                model="gpt-4o-mini",
                rounds=1,
            ),
        )

    finalized = await finalize_analysis_outputs(
        task=SimpleNamespace(product_description="PayPal 诊断"),
        collected=[SimpleNamespace(profile=SimpleNamespace(name="r/paypal"), posts=[{"id": "p1"}])],
        insights={
            "pain_points": [{"description": "p1"}],
            "competitors": [{"name": "PayPal"}],
            "opportunities": [{"description": "o1"}],
            "action_items": [],
        },
        report_tier="A_full",
        facts_v2_quality={"metrics": {"coverage_tier": "full"}},
        settings=SimpleNamespace(enable_llm_summary=True),
        facts_slice={"market_health": {}},
        data_lineage={"source_range": {"posts": 1}},
        posts_analyzed=12,
        comments_analyzed=4,
        posts_db_current=12,
        comments_db_total=4,
        comments_db_eligible=4,
        comments_pipeline_status="ok",
        lookback_days=365,
        cache_hit_rate=0.91,
        ps_ratio_value=0.0,
        pain_counts_by_community={"r/paypal": 3},
        keywords=["paypal"],
        fetch_keywords=["paypal"],
        processing_seconds=42,
        hybrid_posts_count=0,
        hybrid_retrieval_status=None,
        hybrid_retrieval_reason=None,
        hybrid_retrieval_query=None,
        api_call_count=1,
        api_failure_details=[],
        stale_cache_subreddits=[],
        stale_cache_fallback_subreddits=[],
        product_description="PayPal 诊断",
        mode="market_insight",
        audit_level="lab",
        topic_profile_id=None,
        topic_profile_payload=None,
        communities_detail=[{"community": "r/paypal"}],
        duplicate_summary={"duplicate_rate": 0.1},
        dedup_stats={"total_posts": 12},
        post_score_stats={"scored_posts": 12},
        noise_pool_stats={"noise_posts": 0},
        seed_source="semantic",
        data_source_label="reddit",
        coverage_summary={"status_counts": {"DONE_12M": 1}},
        facts_diagnostics={"pipeline": "ok"},
        data_readiness={"ready": True},
        all_remediation_actions=[],
        facts_v2_package={"schema_version": "2.0"},
        knowledge_graph={"nodes": []},
        analysis_blocked_reason=None,
        trend_series=[{"period": "2026-01", "post_count": 12}],
        build_collection_warnings_fn=lambda *_args: [],
        check_trend_views_freshness_fn=_fake_check_trend,
        render_analysis_reports_fn=_fake_render,
    )

    assert finalized.report_html == "<html>ok</html>"
    assert finalized.sources["structured_llm_status"] == "completed"
    assert finalized.sources["llm_used"] is True
    assert finalized.sources["report_structured"]["target_communities"] == ["r/paypal"]
    assert finalized.sources["analysis_audit"]["query_plan_summary"]["intent"] == ""
    assert finalized.sources["analysis_audit"]["final_verdict"]["reason_code"] == "passed"
    assert finalized.sources["analysis_audit"]["final_verdict"]["unique_clickable_reddit_links"] == 2
    assert finalized.confidence_score > 0
