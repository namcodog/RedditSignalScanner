from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.hotpost.signal_input_quality import assess_signal_input_quality
from app.services.hotpost.signal_skill_canary import load_jsonl


EVALS_DIR = ROOT / "reports" / "evals"


def main() -> None:
    cases = load_jsonl(EVALS_DIR / "signal_eval_set_v1.jsonl")
    predictions = {row["eval_case_id"]: row for row in load_jsonl(EVALS_DIR / "signal_judge_full_eval_predictions_v1.jsonl")}
    rows = []
    blocked_fail = 0
    blocked_pass = 0
    for case in cases:
        quality = assess_signal_input_quality(case["input_bundle"])
        pred = predictions[case["eval_case_id"]]
        row = {"eval_case_id": case["eval_case_id"], "sample_origin": case["sample_origin"], "quality": quality, "overall_pass": pred["overall_pass"]}
        rows.append(row)
        if quality["should_block"] and pred["overall_pass"]:
            blocked_pass += 1
        if quality["should_block"] and not pred["overall_pass"]:
            blocked_fail += 1
    (EVALS_DIR / "signal_input_quality_audit_v1.json").write_text(
        json.dumps(
            {
                "sample_count": len(rows),
                "blocked_count": sum(1 for row in rows if row["quality"]["should_block"]),
                "blocked_fail_count": blocked_fail,
                "blocked_pass_count": blocked_pass,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"sample_count": len(rows), "blocked_fail_count": blocked_fail, "blocked_pass_count": blocked_pass}, ensure_ascii=False))


if __name__ == "__main__":
    main()
