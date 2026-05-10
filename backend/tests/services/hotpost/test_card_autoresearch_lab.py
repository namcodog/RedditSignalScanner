from __future__ import annotations

from pathlib import Path

import pytest

from app.services.hotpost.card_autoresearch_lab import build_keep_discard, run_signal_prompt_lab


def test_build_keep_discard_marks_only_winning_variants() -> None:
    rows = build_keep_discard(
        summaries=[
            {"pass_rate": 0.4, "pass_count": 4, "fail_count": 6},
            {"pass_rate": 0.6, "pass_count": 6, "fail_count": 4},
            {"pass_rate": 0.3, "pass_count": 3, "fail_count": 7},
        ],
        variant_ids=["baseline_v1", "better_v1", "worse_v1"],
    )
    assert rows == [
        {"variant_id": "baseline_v1", "pass_rate": 0.4, "pass_count": 4, "fail_count": 6, "decision": "baseline"},
        {"variant_id": "better_v1", "pass_rate": 0.6, "pass_count": 6, "fail_count": 4, "decision": "keep"},
        {"variant_id": "worse_v1", "pass_rate": 0.3, "pass_count": 3, "fail_count": 7, "decision": "discard"},
    ]


@pytest.mark.asyncio
async def test_run_signal_prompt_lab_uses_existing_eval_and_judge_contract() -> None:
    async def fake_variant_runner(case, *, variant_id, model, timeout, rules):
        return {
            "eval_case_id": case["eval_case_id"],
            "input_bundle": case["input_bundle"],
            "baseline_output": {
                "title": f"{variant_id}-title",
                "summary_line": "summary",
                "audience": "audience",
                "why_now": "why_now",
                "detail": {},
            },
        }

    async def fake_judge_runner(case, *, prompt_path: Path):
        return {
            "eval_case_id": case["eval_case_id"],
            "overall_pass": "keep" in case["baseline_output"]["title"],
            "field_passes": {},
            "failure_tags": [],
            "review_notes": "",
        }

    cases = [
        {
            "eval_case_id": "case-1",
            "input_bundle": {"source_scope_id": "ai-automation"},
            "baseline_output": {"title": "old"},
        }
    ]
    result = await run_signal_prompt_lab(
        cases=cases,
        variant_ids=["baseline_v1", "keep_variant_v1"],
        judge_prompt_path=Path("judge.md"),
        model="fake-model",
        timeout=1.0,
        rules={"timeouts": {"signal_seconds": 1}},
        variant_runner=fake_variant_runner,
        judge_runner=fake_judge_runner,
    )
    assert result["variant_results"][0]["summary"]["pass_count"] == 0
    assert result["variant_results"][1]["summary"]["pass_count"] == 1
    assert result["keep_discard"][1]["decision"] == "keep"


@pytest.mark.asyncio
async def test_run_signal_prompt_lab_records_failed_case_without_aborting() -> None:
    async def flaky_variant_runner(case, *, variant_id, model, timeout, rules):
        raise RuntimeError("empty choices")

    async def fake_judge_runner(case, *, prompt_path: Path):
        raise AssertionError("judge should not run after variant failure")

    cases = [
        {
            "eval_case_id": "case-err",
            "input_bundle": {"source_scope_id": "ai-automation"},
            "baseline_output": {"title": "old"},
        }
    ]
    result = await run_signal_prompt_lab(
        cases=cases,
        variant_ids=["baseline_v1"],
        judge_prompt_path=Path("judge.md"),
        model="fake-model",
        timeout=1.0,
        rules={"timeouts": {"signal_seconds": 1}},
        retry_attempts=1,
        variant_runner=flaky_variant_runner,
        judge_runner=fake_judge_runner,
    )
    prediction = result["variant_results"][0]["predictions"][0]
    assert prediction["overall_pass"] is False
    assert prediction["failure_tags"] == ["lab_runtime_error"]
    assert "empty choices" in prediction["review_notes"]
