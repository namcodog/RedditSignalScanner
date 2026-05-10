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
from app.services.hotpost.signal_judge_runner import run_signal_judge
from app.services.hotpost.signal_skill_canary import build_canary_report, load_jsonl, select_canary_cases
from app.services.hotpost.signal_skill_experiment import run_signal_skill_variant


EVALS_DIR = ROOT / "reports" / "evals"
TARGET_PACKS = [("business-growth-ops", "paid-economics"), ("ai-automation", "tools-efficiency")]
VARIANT_ID = "human_summary_tight_why_now_clean_quotes_v2"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


async def main() -> None:
    cases = load_jsonl(EVALS_DIR / "signal_eval_set_v1.jsonl")
    baseline_predictions = load_jsonl(EVALS_DIR / "signal_judge_full_eval_predictions_v1.jsonl")
    baseline_outputs = cases
    selected = select_canary_cases(cases=cases, predictions=baseline_predictions, target_packs=TARGET_PACKS, limit_per_pack=3)
    rules = load_card_content_rules()
    model = load_card_content_models()["fast_model"]
    outputs = []
    predictions = []
    for index, case in enumerate(selected, start=1):
        print(f"[signal-skill-canary] {index}/{len(selected)} {case['eval_case_id']}", flush=True)
        generated = await run_signal_skill_variant(
            case,
            variant_id=VARIANT_ID,
            model=model,
            timeout=float(rules["timeouts"]["signal_seconds"]),
            rules=rules,
            client_factory=None,
        )
        outputs.append(generated)
        predictions.append(await run_signal_judge(generated, prompt_path=EVALS_DIR / "signal_judge_prompt_v1.md"))
    _write_jsonl(EVALS_DIR / "signal_skill_canary_outputs_v1.jsonl", outputs)
    _write_jsonl(EVALS_DIR / "signal_skill_canary_judge_v1.jsonl", predictions)
    (EVALS_DIR / "signal_skill_canary_v1.md").write_text(
        build_canary_report(
            variant_id=VARIANT_ID,
            baseline_predictions=baseline_predictions,
            canary_predictions=predictions,
            baseline_outputs=baseline_outputs,
            canary_outputs=outputs,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"variant_id": VARIANT_ID, "sample_count": len(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
