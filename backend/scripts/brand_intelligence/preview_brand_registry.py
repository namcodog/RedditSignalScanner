from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.scripts_support.env_loader import load_backend_env

load_backend_env()

from app.db.session import SessionFactory
from app.services.brand_intelligence.brand_registry_reader import (
    read_brand_registry_view,
    render_brand_registry_view_markdown,
)

TODAY = date.today().isoformat()
REPORT_DIR = PROJECT_ROOT / "reports" / "brand-intelligence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview read-only brand registry view."
    )
    parser.add_argument("--status")
    parser.add_argument("--interest-tag")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--profile", default="consumer_safe")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPORT_DIR / f"brand-registry-view-{TODAY}.json",
    )
    parser.add_argument(
        "--md-output", type=Path, default=REPORT_DIR / f"brand-registry-view-{TODAY}.md"
    )
    return parser.parse_args()


async def build_payload(args: argparse.Namespace) -> dict[str, object]:
    async with SessionFactory() as session:
        return await read_brand_registry_view(
            session,
            status_filter=args.status,
            interest_tag_filter=args.interest_tag,
            limit=int(args.limit),
            consumer_profile_id=str(args.profile),
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
        render_brand_registry_view_markdown(payload), encoding="utf-8"
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
