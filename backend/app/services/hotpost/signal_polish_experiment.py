from __future__ import annotations

from typing import Optional, Any

from app.services.hotpost.signal_polish_variant_policy import apply_signal_polish_variant
from app.services.hotpost.signal_skill_experiment import run_signal_skill_variant


BASELINE_SIGNAL_PROMPT_VARIANT = "human_summary_tight_why_now_v1"


async def run_signal_polish_variant(
    case: dict[str, Any],
    *,
    variant_id: str,
    model: str,
    timeout: float,
    rules: dict[str, Any],
    client_factory:Optional[ Any] = None,
) -> dict[str, Any]:
    baseline = await run_signal_skill_variant(
        case,
        variant_id=BASELINE_SIGNAL_PROMPT_VARIANT,
        model=model,
        timeout=timeout,
        rules=rules,
        client_factory=client_factory,
    )
    return {
        **baseline,
        "variant_id": variant_id,
        "baseline_output": apply_signal_polish_variant(
            baseline["baseline_output"],
            input_bundle=case["input_bundle"],
            variant_id=variant_id,
        ),
    }


__all__ = ["BASELINE_SIGNAL_PROMPT_VARIANT", "run_signal_polish_variant"]
