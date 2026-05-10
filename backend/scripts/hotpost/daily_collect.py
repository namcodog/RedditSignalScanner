from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile
from app.services.hotpost.quota_aware_collect_runner import run_quota_aware_collect


def _resolve_scope(*, scope: str | None, all_scope: bool) -> str | None:
    if all_scope:
        return None
    return scope


async def main() -> None:
    load_backend_env()
    collect_defaults = get_supply_collect_profile("safe")
    parser = argparse.ArgumentParser(description="Hotpost 日更抓取")
    parser.add_argument("--scope", help="Restrict collect to one scope. Omit to use the product default: all-scope.")
    parser.add_argument("--all-scope", action="store_true", help="Explicitly collect every configured scope.")
    parser.add_argument("--mode", choices=["safe", "harvest"], default="safe")
    parser.add_argument("--max-candidates", type=int, default=collect_defaults["max_candidates_per_scope"])
    parser.add_argument("--dry-cycle", type=int, default=int(collect_defaults.get("dry_cycle") or 3))
    args = parser.parse_args()
    summary = await run_quota_aware_collect(
        scope=_resolve_scope(scope=args.scope, all_scope=args.all_scope),
        mode=args.mode,
        max_candidates=args.max_candidates,
        dry_cycle_limit=args.dry_cycle,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
