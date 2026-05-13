from __future__ import annotations

from pathlib import Path

import pytest

from app.services.hotpost.signal_judge_runner import compare_judgments, run_signal_judge, summarize_predictions


class _FakeClient:
    async def generate(self, prompt, *, response_format=None, temperature=0.7, max_tokens=2048) -> str:
        return '{"overall_pass": true, "field_passes": {"title": true, "summary_line": true, "audience": true, "why_now": false}, "failure_tags": ["why_now_not_actionable"], "review_notes": "有判断，但 why_now 还弱。"}'


def _factory(model: str, timeout: float) -> _FakeClient:
    return _FakeClient()


@pytest.mark.asyncio
async def test_run_signal_judge_parses_json_payload(tmp_path: Path) -> None:
    prompt_path = tmp_path / "judge.md"
    prompt_path.write_text("judge prompt", encoding="utf-8")
    case = {
        "eval_case_id": "case-1",
        "input_bundle": {"source_scope_id": "ai-automation"},
        "baseline_output": {"title": "title"},
    }

    result = await run_signal_judge(case, prompt_path=prompt_path, client_factory=_factory)

    assert result["eval_case_id"] == "case-1"
    assert result["overall_pass"] is True
    assert result["failure_tags"] == ["why_now_not_actionable"]


def test_compare_judgments_reports_mismatches() -> None:
    summary = compare_judgments(
        predictions=[{"eval_case_id": "case-1", "overall_pass": True, "failure_tags": []}],
        labels=[{"eval_case_id": "case-1", "overall_pass": False, "failure_tags": ["no_judgment_gain"]}],
    )

    assert summary["sample_count"] == 1
    assert summary["overall_match_count"] == 0
    assert summary["exact_tag_match_count"] == 0
    assert summary["mismatches"][0]["eval_case_id"] == "case-1"


def test_summarize_predictions_reports_distribution() -> None:
    summary = summarize_predictions(
        [
            {"eval_case_id": "case-1", "overall_pass": True, "failure_tags": []},
            {"eval_case_id": "case-2", "overall_pass": False, "failure_tags": ["reddit_restatement", "no_judgment_gain"]},
            {"eval_case_id": "case-3", "overall_pass": False, "failure_tags": ["reddit_restatement"]},
        ],
        [
            {"eval_case_id": "case-1", "input_bundle": {"source_scope_id": "ai-automation"}},
            {"eval_case_id": "case-2", "input_bundle": {"source_scope_id": "ai-automation"}},
            {"eval_case_id": "case-3", "input_bundle": {"source_scope_id": "ecommerce-sellers"}},
        ],
    )

    assert summary["sample_count"] == 3
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 2
    assert summary["top_failure_tags"][0] == ("reddit_restatement", 2)
    assert summary["scope_pass_counts"] == {"ai-automation": 1}
