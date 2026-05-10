from __future__ import annotations

from app.services.hotpost.signal_skill_canary import build_canary_report, select_canary_cases


def test_select_canary_cases_only_picks_failed_candidate_generated_rows() -> None:
    cases = [
        {"eval_case_id": "a", "sample_origin": "candidate_generated", "input_bundle": {"source_scope_id": "business-growth-ops", "topic_pack_id": "paid-economics"}},
        {"eval_case_id": "b", "sample_origin": "published_validate", "input_bundle": {"source_scope_id": "business-growth-ops", "topic_pack_id": "paid-economics"}},
        {"eval_case_id": "c", "sample_origin": "candidate_generated", "input_bundle": {"source_scope_id": "ai-automation", "topic_pack_id": "tools-efficiency"}},
    ]
    predictions = [
        {"eval_case_id": "a", "overall_pass": False},
        {"eval_case_id": "b", "overall_pass": False},
        {"eval_case_id": "c", "overall_pass": True},
    ]
    picked = select_canary_cases(
        cases=cases,
        predictions=predictions,
        target_packs=[("business-growth-ops", "paid-economics"), ("ai-automation", "tools-efficiency")],
    )
    assert [item["eval_case_id"] for item in picked] == ["a"]


def test_select_canary_cases_deduplicates_same_eval_case() -> None:
    cases = [
        {"eval_case_id": "a", "sample_origin": "candidate_generated", "input_bundle": {"source_scope_id": "business-growth-ops", "topic_pack_id": "paid-economics"}},
    ]
    predictions = [
        {"eval_case_id": "a", "overall_pass": False},
        {"eval_case_id": "a", "overall_pass": False},
    ]
    picked = select_canary_cases(
        cases=cases,
        predictions=predictions,
        target_packs=[("business-growth-ops", "paid-economics")],
        limit_per_pack=3,
    )
    assert [item["eval_case_id"] for item in picked] == ["a"]


def test_build_canary_report_marks_improvement() -> None:
    report = build_canary_report(
        variant_id="human_summary_tight_why_now_v1",
        baseline_predictions=[{"eval_case_id": "a", "overall_pass": False, "failure_tags": ["reddit_restatement"]}],
        canary_predictions=[{"eval_case_id": "a", "overall_pass": True, "failure_tags": []}],
        baseline_outputs=[{"eval_case_id": "a", "baseline_output": {"title": "旧", "summary_line": "旧摘要", "why_now": "旧why"}}],
        canary_outputs=[{"eval_case_id": "a", "baseline_output": {"title": "新", "summary_line": "新摘要", "why_now": "新why"}}],
    )
    assert "- improved: `1`" in report
    assert "- baseline: `fail` / ['reddit_restatement']" in report
    assert "- canary: `pass` / []" in report
