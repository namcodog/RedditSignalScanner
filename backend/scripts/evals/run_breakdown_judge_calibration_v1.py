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

from app.services.hotpost.signal_eval_review_packet_builder import load_jsonl
from app.services.hotpost.signal_judge_runner import compare_judgments, run_signal_judge


EVALS_DIR = ROOT / "reports" / "evals"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


async def main() -> None:
    cases = load_jsonl(EVALS_DIR / "breakdown_eval_set_v1.jsonl")
    labels = load_jsonl(EVALS_DIR / "breakdown_judge_calibration_labels_v1.jsonl")
    label_ids = {item["eval_case_id"] for item in labels}
    selected = [case for case in cases if case["eval_case_id"] in label_ids]
    predictions = []
    for index, case in enumerate(selected, start=1):
        print(f"[breakdown-judge] {index}/{len(selected)} {case['eval_case_id']}", flush=True)
        predictions.append(await run_signal_judge(case, prompt_path=EVALS_DIR / "breakdown_judge_prompt_v1.md"))
    summary = compare_judgments(predictions=predictions, labels=labels)
    _write_jsonl(EVALS_DIR / "breakdown_judge_calibration_predictions_v1.jsonl", predictions)
    (EVALS_DIR / "breakdown_judge_calibration_summary_v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
