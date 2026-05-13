from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.services.brand_intelligence.archive_brand_pool_outputs import (
    write_archive_brand_pool_outputs,
)
from app.services.brand_intelligence.archive_brand_pool_review import (
    build_archive_brand_pool_review,
)


def parse_args() -> argparse.Namespace:
    report_date = date.today().isoformat()
    output_dir = PROJECT_ROOT / "reports" / "brand-intelligence"
    parser = argparse.ArgumentParser(
        description="Generate user-vetted archive brand pool preaudit."
    )
    parser.add_argument("--date", default=report_date)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=output_dir / f"archive-brand-pool-preaudit-{report_date}.json",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=output_dir / f"archive-brand-pool-preaudit-{report_date}.md",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=output_dir / f"archive-brand-pool-preaudit-{report_date}.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_archive_brand_pool_review()
    write_archive_brand_pool_outputs(
        report,
        json_path=args.json_output,
        md_path=args.md_output,
        csv_path=args.csv_output,
    )
    print(
        json.dumps(
            {
                **report.summary,
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "csv_output": str(args.csv_output),
                "report_date": str(args.date),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
