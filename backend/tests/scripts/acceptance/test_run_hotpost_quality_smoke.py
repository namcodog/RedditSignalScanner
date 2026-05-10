from __future__ import annotations

from scripts.acceptance.run_hotpost_quality_smoke import (
    DEFAULT_CASES,
    _build_summary,
    _extract_case_result,
    _resolve_cases,
)


def test_resolve_cases_defaults_to_low_cost_matrix() -> None:
    cases = _resolve_cases([], limit=2)

    assert cases == list(DEFAULT_CASES[:2])


def test_extract_case_result_reads_debug_metrics() -> None:
    payload = {
        "query_id": "demo-id",
        "query": "reddit scheduling tool",
        "mode": "opportunity",
        "status": "degraded",
        "summary": "summary",
        "evidence_count": 12,
        "communities": ["r/test", "r/startups"],
        "debug_info": {
            "quality_contract_gaps": ["missing_market_signal"],
            "degraded_reasons": ["quality_contract:missing_market_signal"],
            "reasoning_triggered": True,
            "final_report_layer": "reasoning",
            "report_model_name": "openai/gpt-5.4-mini",
            "fast_model_name": "google/gemini-2.5-flash-lite",
            "reasoning_model_name": "openai/gpt-5.4-mini",
            "report_source": "llm",
            "report_degraded_reason": "",
        },
    }

    result = _extract_case_result(
        payload,
        fallback_query="fallback query",
        fallback_mode="opportunity",
    )

    assert result["reasoning_triggered"] is True
    assert result["final_report_layer"] == "reasoning"
    assert result["quality_gap_count"] == 1
    assert result["community_count"] == 2


def test_build_summary_counts_reasoning_and_layers() -> None:
    summary = _build_summary(
        [
            {
                "evidence_count": 10,
                "quality_gap_count": 0,
                "reasoning_triggered": False,
                "status": "completed",
                "degraded_reasons": [],
                "final_report_layer": "fast",
                "report_source": "llm",
            },
            {
                "evidence_count": 14,
                "quality_gap_count": 2,
                "reasoning_triggered": True,
                "status": "degraded",
                "degraded_reasons": ["quality_contract:missing_market_signal"],
                "final_report_layer": "reasoning",
                "report_source": "llm",
            },
        ]
    )

    assert summary["total_cases"] == 2
    assert summary["reasoning_triggered_cases"] == 1
    assert summary["fast_only_cases"] == 1
    assert summary["degraded_cases"] == 1
    assert summary["total_quality_gap_count"] == 2
    assert summary["final_report_layers"] == {"fast": 1, "reasoning": 1}
