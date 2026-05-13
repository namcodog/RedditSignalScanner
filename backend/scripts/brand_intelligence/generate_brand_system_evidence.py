from __future__ import annotations

import argparse
import asyncio
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.scripts_support.env_loader import load_backend_env

load_backend_env()

from app.db.session import SessionFactory
from app.services.brand_intelligence.brand_system_evidence import (
    load_brand_system_evidence,
)
from app.services.brand_intelligence.brand_system_evidence_outputs import (
    render_brand_system_evidence_markdown,
)

TODAY = date.today().isoformat()
REPORT_DIR = PROJECT_ROOT / "reports" / "brand-intelligence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate backend-only brand evidence pack."
    )
    parser.add_argument("--profile", default="system_evidence")
    parser.add_argument("--min-mentions", type=int, default=1)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPORT_DIR / f"brand-system-evidence-{TODAY}.json",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=REPORT_DIR / f"brand-system-evidence-{TODAY}.md",
    )
    return parser.parse_args()


async def build_payload(args: argparse.Namespace) -> dict[str, object]:
    async with SessionFactory() as session:
        return await load_brand_system_evidence(
            session,
            profile_id=str(args.profile),
            min_mentions=int(args.min_mentions),
            limit=int(args.limit),
        )


def main() -> None:
    args = parse_args()
    payload = asyncio.run(build_payload(args))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.md_output.write_text(
        render_brand_system_evidence_markdown(payload), encoding="utf-8"
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
