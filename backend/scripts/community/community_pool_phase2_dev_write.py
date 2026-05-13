from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.community.community_category_map_service import (
    replace_community_category_map,
)
from app.services.community.community_pool_phase2_dev_writer import (
    PoolInsertRow,
    build_pool_insert_rows,
    build_write_plan,
    render_rollback_sql,
)
from scripts.import_safety import add_execute_flag, ensure_dev_or_test_database, is_dry_run

DEFAULT_INPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase1-dry-run.json"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "community-governance" / "phase2-dev-write-result.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase2-dev-write.md"
DEFAULT_ROLLBACK_SQL = (
    PROJECT_ROOT / "reports" / "community-governance" / "phase2-dev-write-rollback.sql"
)


async def _existing_name_sets(
    names: list[str],
) -> tuple[set[str], set[str]]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(CommunityPool.name, CommunityPool.deleted_at).where(
                CommunityPool.name.in_(names)
            )
        )
        active: set[str] = set()
        deleted: set[str] = set()
        for name, deleted_at in result.all():
            if deleted_at is None:
                active.add(str(name))
            else:
                deleted.add(str(name))
        return active, deleted


async def _insert_rows(rows: list[PoolInsertRow]) -> list[str]:
    inserted: list[tuple[CommunityPool, PoolInsertRow]] = []
    async with SessionFactory() as session:
        for row in rows:
            community = CommunityPool(
                name=row.name,
                tier=row.tier,
                categories=row.categories,
                description_keywords=row.description_keywords,
                daily_posts=row.daily_posts,
                avg_comment_length=row.avg_comment_length,
                quality_score=row.quality_score,
                priority=row.priority,
                is_active=True,
            )
            session.add(community)
            inserted.append((community, row))
        await session.flush()
        for community, row in inserted:
            await replace_community_category_map(
                session,
                community_id=community.id,
                categories=row.categories,
            )
        await session.commit()
    return [row.name for _, row in inserted]


async def _current_database() -> str:
    async with SessionFactory() as session:
        return str((await session.execute(text("select current_database()"))).scalar_one())


async def build_result_payload(*, input_path: Path, dry_run: bool) -> dict[str, Any]:
    guard_db = ensure_dev_or_test_database()
    current_db = await _current_database()
    if current_db != guard_db:
        raise RuntimeError(f"database guard mismatch: guard={guard_db}, current={current_db}")

    phase1_payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = build_pool_insert_rows(phase1_payload)
    active_existing, deleted_existing = await _existing_name_sets([row.name for row in rows])
    plan = build_write_plan(
        rows,
        active_existing=active_existing,
        deleted_existing=deleted_existing,
    )

    if plan.blocked_deleted_conflicts and not dry_run:
        conflicts = ", ".join(plan.blocked_deleted_conflicts)
        raise RuntimeError(f"refusing write because soft-deleted conflicts exist: {conflicts}")

    inserted_names: list[str] = []
    if not dry_run and plan.insert_rows:
        inserted_names = await _insert_rows(plan.insert_rows)

    summary = {
        **plan.summary,
        "inserted": len(inserted_names),
    }
    rollback_target_names = inserted_names if not dry_run else [row.name for row in plan.insert_rows]
    return {
        "phase": "community-pool-phase2-dev-write",
        "dry_run": dry_run,
        "database": current_db,
        "summary": summary,
        "planned_insert_names": [row.name for row in plan.insert_rows],
        "inserted_names": inserted_names,
        "skipped_existing": plan.skipped_existing,
        "blocked_deleted_conflicts": plan.blocked_deleted_conflicts,
        "rollback_target_names": rollback_target_names,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Phase 2 Community Pool Dev Write",
        "",
        f"- DB writes: `{'false' if payload['dry_run'] else 'true'}`",
        f"- target_database: `{payload['database']}`",
        f"- input_rows: `{summary['input_rows']}`",
        f"- would_insert: `{summary['would_insert']}`",
        f"- inserted: `{summary['inserted']}`",
        f"- skipped_existing: `{summary['skipped_existing']}`",
        f"- blocked_deleted_conflicts: `{summary['blocked_deleted_conflicts']}`",
        f"- rollback_sql: `{payload.get('rollback_sql', '')}`",
        "",
        "## Skipped Existing",
        "",
    ]
    skipped = payload.get("skipped_existing") or []
    lines.extend(f"- {name}" for name in skipped)
    if not skipped:
        lines.append("- none")
    lines.extend(["", "## Inserted Names", ""])
    inserted = payload.get("inserted_names") or []
    lines.extend(f"- {name}" for name in inserted)
    if not inserted:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write approved Phase 1 community additions into Dev community_pool."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--rollback-sql", type=Path, default=DEFAULT_ROLLBACK_SQL)
    add_execute_flag(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = is_dry_run(args)
    payload = asyncio.run(build_result_payload(input_path=args.input, dry_run=dry_run))
    payload["rollback_sql"] = str(args.rollback_sql.relative_to(PROJECT_ROOT))
    rollback_sql = render_rollback_sql(payload["rollback_target_names"])

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.md_output.write_text(render_markdown(payload), encoding="utf-8")
    args.rollback_sql.write_text(rollback_sql, encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
