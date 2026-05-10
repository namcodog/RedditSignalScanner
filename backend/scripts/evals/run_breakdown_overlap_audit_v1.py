from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.hotpost.breakdown_overlap_audit import audit_breakdown_overlap


EVALS_DIR = ROOT / "reports" / "evals"


def main() -> None:
    summary = audit_breakdown_overlap()
    (EVALS_DIR / "breakdown_overlap_audit_v1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
