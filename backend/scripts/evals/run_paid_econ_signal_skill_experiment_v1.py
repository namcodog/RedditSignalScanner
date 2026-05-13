from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _is_placeholder(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized.startswith("your_") or "example" in normalized or normalized == "replace_me"


for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
    if value is not None and _is_placeholder(os.getenv(key)):
        os.environ[key] = str(value)

from app.services.hotpost.card_content_generator import load_card_content_models, load_card_content_rules
from app.services.hotpost.signal_judge_runner import run_signal_judge, summarize_predictions
from app.services.hotpost.signal_pack_eval_builder import build_signal_pack_eval_cases
from app.services.hotpost.signal_skill_experiment import run_signal_skill_variant


EVALS_DIR = ROOT / "reports" / "evals"
VARIANTS = [
    "human_summary_tight_why_now_v1",
    "paid_econ_decision_v1",
    "paid_econ_decision_strict_v1",
]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


async def _run_variant(variant_id: str, cases: list[dict]) -> dict:
    rules = load_card_content_rules()
    model = load_card_content_models()["fast_model"]
    rows = []
    for case in cases:
        generated = await run_signal_skill_variant(
            case,
            variant_id=variant_id,
            model=model,
            timeout=float(rules["timeouts"]["signal_seconds"]),
            rules=rules,
            client_factory=None,
        )
        prediction = await run_signal_judge(generated, prompt_path=EVALS_DIR / "signal_judge_prompt_v1.md")
        rows.append((generated, prediction))
    generated_rows = [item[0] for item in rows]
    predictions = [item[1] for item in rows]
    return {"generated_rows": generated_rows, "predictions": predictions, "summary": summarize_predictions(predictions, generated_rows)}


async def main() -> None:
    cohort = await build_signal_pack_eval_cases(source_scope_id="business-growth-ops", topic_pack_id="paid-economics")
    cases = cohort["cases"]
    (EVALS_DIR / "paid_econ_signal_eval_cohort_v1.json").write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    keep_discard = []
    baseline_rate = None
    for variant_id in VARIANTS:
        result = await _run_variant(variant_id, cases)
        _write_jsonl(EVALS_DIR / f"paid_econ_signal_skill_{variant_id}_outputs_v1.jsonl", result["generated_rows"])
        _write_jsonl(EVALS_DIR / f"paid_econ_signal_skill_{variant_id}_judge_v1.jsonl", result["predictions"])
        (EVALS_DIR / f"paid_econ_signal_skill_{variant_id}_summary_v1.json").write_text(
            json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rate = float(result["summary"]["pass_rate"])
        if baseline_rate is None:
            baseline_rate = rate
        keep_discard.append(
            {
                "variant_id": variant_id,
                "pass_rate": rate,
                "pass_count": result["summary"]["pass_count"],
                "fail_count": result["summary"]["fail_count"],
                "decision": "baseline" if variant_id == VARIANTS[0] else ("keep" if rate > baseline_rate else "discard"),
            }
        )
    (EVALS_DIR / "paid_econ_signal_skill_keep_discard_v1.json").write_text(
        json.dumps(keep_discard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(keep_discard, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
