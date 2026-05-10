from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Any, Awaitable, Callable

from app.services.hotpost.signal_judge_runner import run_signal_judge, summarize_predictions
from app.services.hotpost.signal_skill_experiment import run_signal_skill_variant

SignalVariantRunner = Callable[..., Awaitable[dict[str, Any]]]
SignalJudgeRunner = Callable[..., Awaitable[dict[str, Any]]]


async def run_signal_prompt_lab(
    *,
    cases: list[dict[str, Any]],
    variant_ids: list[str],
    judge_prompt_path: Path,
    model: str,
    timeout: float,
    rules: dict[str, Any],
    concurrency: int = 4,
    retry_attempts: int = 2,
    variant_runner: SignalVariantRunner = run_signal_skill_variant,
    judge_runner: SignalJudgeRunner = run_signal_judge,
) -> dict[str, Any]:
    variant_results: list[dict[str, Any]] = []
    for variant_id in variant_ids:
        semaphore = asyncio.Semaphore(concurrency)

        async def _worker(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            async with semaphore:
                last_error:Optional[ Exception] = None
                for _ in range(max(retry_attempts, 1)):
                    try:
                        generated = await variant_runner(
                            case,
                            variant_id=variant_id,
                            model=model,
                            timeout=timeout,
                            rules=rules,
                        )
                        prediction = await judge_runner(generated, prompt_path=judge_prompt_path)
                        return generated, prediction
                    except Exception as exc:  # pragma: no cover - exercised via retry test
                        last_error = exc
                return _build_failed_generated(case, variant_id=variant_id), _build_failed_prediction(
                    case,
                    error=last_error,
                )

        rows = await asyncio.gather(*[_worker(case) for case in cases])
        generated_rows = [item[0] for item in rows]
        predictions = [item[1] for item in rows]
        variant_results.append(
            {
                "variant_id": variant_id,
                "generated_rows": generated_rows,
                "predictions": predictions,
                "summary": summarize_predictions(predictions, generated_rows),
            }
        )
    return {
        "variant_results": variant_results,
        "keep_discard": build_keep_discard(
            summaries=[item["summary"] for item in variant_results],
            variant_ids=variant_ids,
        ),
    }


def _build_failed_generated(case: dict[str, Any], *, variant_id: str) -> dict[str, Any]:
    return {
        "eval_case_id": case["eval_case_id"],
        "variant_id": variant_id,
        "input_bundle": case["input_bundle"],
        "baseline_output": case.get("baseline_output") or {},
    }


def _build_failed_prediction(case: dict[str, Any], *, error:Optional[ Exception]) -> dict[str, Any]:
    return {
        "eval_case_id": case["eval_case_id"],
        "overall_pass": False,
        "field_passes": {},
        "failure_tags": ["lab_runtime_error"],
        "review_notes": str(error or "lab runtime error")[:240],
    }


def build_keep_discard(*, summaries: list[dict[str, Any]], variant_ids: list[str]) -> list[dict[str, Any]]:
    baseline_id = variant_ids[0]
    baseline_rate = float(summaries[0]["pass_rate"])
    rows: list[dict[str, Any]] = []
    for variant_id, summary in zip(variant_ids, summaries, strict=True):
        rate = float(summary["pass_rate"])
        decision = "baseline" if variant_id == baseline_id else ("keep" if rate > baseline_rate else "discard")
        rows.append(
            {
                "variant_id": variant_id,
                "pass_rate": rate,
                "pass_count": int(summary["pass_count"]),
                "fail_count": int(summary["fail_count"]),
                "decision": decision,
            }
        )
    return rows


__all__ = ["build_keep_discard", "run_signal_prompt_lab"]
