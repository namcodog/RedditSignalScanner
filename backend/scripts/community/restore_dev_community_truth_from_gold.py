from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database_guard import validate_database_target
from app.services.community.gold_dev_community_restore_service import (
    apply_community_restore_plan,
    load_gold_community_restore_plan,
)

DEFAULT_GOLD_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner"
DEFAULT_DEV_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev"


def _build_sessionmaker(database_url: str, *, allow_gold: bool) -> async_sessionmaker[AsyncSession]:
    validate_database_target(database_url, allow_gold_db=allow_gold)
    engine = create_async_engine(database_url, pool_pre_ping=True, future=True, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _build_output_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    reports_dir = root / "reports" / "local-acceptance"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir / f"gold_dev_restore_{int(time.time())}.json"


async def _run(*, dry_run: bool, output: Path) -> dict[str, object]:
    gold_factory = _build_sessionmaker(
        os.getenv("GOLD_DATABASE_URL", DEFAULT_GOLD_URL),
        allow_gold=True,
    )
    dev_factory = _build_sessionmaker(
        os.getenv("DEV_DATABASE_URL", DEFAULT_DEV_URL),
        allow_gold=False,
    )
    async with gold_factory() as gold_session, dev_factory() as dev_session:
        plan = await load_gold_community_restore_plan(gold_session, dev_session)
        result = await apply_community_restore_plan(
            dev_session,
            plan=plan,
            dry_run=dry_run,
        )
    payload = {
        "dry_run": dry_run,
        "result": {
            "pool_upserts": result.pool_upserts,
            "cache_upserts": result.cache_upserts,
            "pool_deactivated": result.pool_deactivated,
            "cache_deactivated": result.cache_deactivated,
            "truth_registry_retired": result.truth_registry_retired,
            "truth_runtime_paused": result.truth_runtime_paused,
            "truth_membership_archived": result.truth_membership_archived,
            "truth_governance_archived": result.truth_governance_archived,
        },
        "plan": {
            "pool_snapshot_count": len(plan.pool_snapshots),
            "cache_snapshot_count": len(plan.cache_snapshots),
            "deactivate_pool_count": len(plan.deactivate_pool_names),
            "deactivate_cache_count": len(plan.deactivate_cache_names),
            "deactivate_pool_sample": plan.deactivate_pool_names[:20],
            "deactivate_cache_sample": plan.deactivate_cache_names[:20],
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore dev community truth from gold DB.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually write into dev DB. Default is dry-run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output json path.",
    )
    args = parser.parse_args()
    output = args.output or _build_output_path()
    payload = asyncio.run(_run(dry_run=not args.write, output=output))
    print(json.dumps({"output": str(output), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
