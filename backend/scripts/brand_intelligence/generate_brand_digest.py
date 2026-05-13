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

from app.services.brand_intelligence.brand_digest import (
    build_brand_digest_from_catalog,
    load_default_catalog,
    write_brand_digest_outputs,
)
from app.services.hotpost.card_payload_store import load_published_cards


def parse_args() -> argparse.Namespace:
    report_date = date.today().isoformat()
    output_dir = PROJECT_ROOT / "reports" / "brand-intelligence"
    parser = argparse.ArgumentParser(
        description="Generate a dry-run brand intelligence digest."
    )
    parser.add_argument("--date", default=report_date)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=output_dir / f"brand-digest-{report_date}.json",
    )
    parser.add_argument(
        "--md-output", type=Path, default=output_dir / f"brand-digest-{report_date}.md"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_brand_digest_from_catalog(
        load_published_cards(),
        catalog=load_default_catalog(),
        report_date=str(args.date),
    )
    write_brand_digest_outputs(
        report, json_path=args.json_output, md_path=args.md_output
    )
    summary = report.to_payload()["summary"]
    assert isinstance(summary, dict)
    print(
        json.dumps(
            {
                **summary,
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
