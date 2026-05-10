from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.breakdown_draft_materializer import materialize_breakdown_drafts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize write drafts from current breakdown suggestions.")
    parser.add_argument("--scope", default=None, help="Restrict materialization to a single source scope.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum breakdown suggestions to materialize.")
    return parser


async def _run(args: argparse.Namespace) -> dict[str, object]:
    load_backend_env()
    results = await materialize_breakdown_drafts(source_scope_id=args.scope, limit=int(args.limit or 20))
    return {
        "count": len(results),
        "materialized": sum(item.status == "materialized" for item in results),
        "skipped_existing": sum(item.status == "skipped_existing" for item in results),
        "failed": sum(item.status == "failed" for item in results),
        "items": [item.model_dump(mode="json") for item in results],
    }


def main() -> None:
    args = _build_parser().parse_args()
    payload = asyncio.run(_run(args))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
