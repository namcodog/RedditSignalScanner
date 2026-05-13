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

from app.services.brand_intelligence.source_catalog import (
    load_brand_source_catalog,
    write_brand_source_catalog_outputs,
)


def parse_args() -> argparse.Namespace:
    report_date = date.today().isoformat()
    output_dir = PROJECT_ROOT / "reports" / "brand-intelligence"
    parser = argparse.ArgumentParser(
        description="Generate a brand source catalog audit."
    )
    parser.add_argument("--date", default=report_date)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=output_dir / f"brand-source-catalog-{report_date}.json",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=output_dir / f"brand-source-catalog-{report_date}.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = load_brand_source_catalog()
    write_brand_source_catalog_outputs(
        catalog, json_path=args.json_output, md_path=args.md_output
    )
    print(
        json.dumps(
            {
                **catalog.summary,
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "report_date": str(args.date),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
