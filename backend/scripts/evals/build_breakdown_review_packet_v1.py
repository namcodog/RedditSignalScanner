from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.hotpost.breakdown_eval_review_packet_builder import (
    build_breakdown_failure_taxonomy,
    build_breakdown_review_packet,
    load_jsonl,
)


EVALS_DIR = ROOT / "reports" / "evals"


def main() -> None:
    cases = load_jsonl(EVALS_DIR / "breakdown_eval_set_v1.jsonl")
    labels = load_jsonl(EVALS_DIR / "breakdown_eval_labels_v1.jsonl")
    packet = build_breakdown_review_packet(cases, labels)
    taxonomy = build_breakdown_failure_taxonomy(cases)
    (EVALS_DIR / "breakdown_eval_review_packet_v1.md").write_text(packet, encoding="utf-8")
    (EVALS_DIR / "breakdown_failure_taxonomy_v1.md").write_text(taxonomy, encoding="utf-8")
    print(f"review_cases={len(cases)} labels={len(labels)}")


if __name__ == "__main__":
    main()
