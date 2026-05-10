from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.community_discovery_audit import build_current_community_discovery_audit


def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Audit probe-only Hotpost experimental communities")
    parser.add_argument("--date", default=date.today().isoformat(), help="Report date in YYYY-MM-DD format.")
    parser.add_argument(
        "--output-dir",
        default="reports/community-governance",
        help="Directory for the read-only audit report.",
    )
    args = parser.parse_args()
    report_date = date.fromisoformat(args.date)
    report = build_current_community_discovery_audit(report_date=report_date)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"community-discovery-audit-{report_date.isoformat()}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), "row_count": len(report["rows"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
