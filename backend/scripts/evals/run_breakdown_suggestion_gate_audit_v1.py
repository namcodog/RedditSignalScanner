from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.hotpost.breakdown_suggestion_quality import assess_breakdown_suggestion_coherence
from app.services.hotpost.card_candidate_store import get_candidates
from app.services.hotpost.signal_eval_review_packet_builder import load_jsonl


EVALS_DIR = ROOT / "reports" / "evals"


def main() -> None:
    cases = [case for case in load_jsonl(EVALS_DIR / "breakdown_eval_set_v1.jsonl") if case["sample_origin"] == "suggestion_write"]
    labels = {row["eval_case_id"]: row for row in load_jsonl(EVALS_DIR / "breakdown_judge_calibration_labels_v1.jsonl")}
    blocked_fail = blocked_pass = allowed_fail = allowed_pass = 0
    rows = []
    for case in cases:
        quality = assess_breakdown_suggestion_coherence(get_candidates(case["input_bundle"]["candidate_ids"]))
        human_pass = bool(labels[case["eval_case_id"]]["overall_pass"])
        if quality["should_block"] and human_pass:
            blocked_pass += 1
        elif quality["should_block"]:
            blocked_fail += 1
        elif human_pass:
            allowed_pass += 1
        else:
            allowed_fail += 1
        rows.append(
            {
                "eval_case_id": case["eval_case_id"],
                "human_pass": human_pass,
                "should_block": quality["should_block"],
                "reasons": quality["reasons"],
                "shared_anchors": quality["shared_anchors"],
            }
        )
    summary = {
        "sample_count": len(cases),
        "blocked_fail_count": blocked_fail,
        "blocked_pass_count": blocked_pass,
        "allowed_fail_count": allowed_fail,
        "allowed_pass_count": allowed_pass,
        "rows": rows,
    }
    (EVALS_DIR / "breakdown_suggestion_gate_audit_v1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
