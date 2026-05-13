from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env

load_backend_env()

from app.db.session import SessionFactory
from app.services.brand_intelligence.brand_registry_plan import (
    build_brand_registry_plan,
)
from app.services.brand_intelligence.brand_registry_writer import (
    apply_brand_registry_plan,
)
from scripts.import_safety import (
    add_execute_flag,
    ensure_dev_or_test_database,
    is_dry_run,
)

TODAY = date.today().isoformat()
REPORT_DIR = PROJECT_ROOT / "reports" / "brand-intelligence"
DEFAULT_STRICT_INPUT = REPORT_DIR / f"archive-brand-pool-strict-audit-{TODAY}.json"
DEFAULT_QUALITY_INPUT = REPORT_DIR / f"brand-quality-review-{TODAY}.json"
DEFAULT_DIGEST_INPUT = REPORT_DIR / f"brand-digest-{TODAY}.json"
DEFAULT_JSON_OUTPUT = REPORT_DIR / f"brand-registry-r15-2-dev-write-{TODAY}.json"
DEFAULT_MD_OUTPUT = REPORT_DIR / f"brand-registry-r15-2-dev-write-{TODAY}.md"
DEFAULT_ROLLBACK_SQL = (
    REPORT_DIR / f"brand-registry-r15-2-dev-write-rollback-{TODAY}.sql"
)


async def _current_database() -> str:
    async with SessionFactory() as session:
        return str(
            (await session.execute(text("select current_database()"))).scalar_one()
        )


async def build_result_payload(args: argparse.Namespace) -> dict[str, Any]:
    guard_db = ensure_dev_or_test_database()
    current_db = await _current_database()
    if current_db != guard_db:
        raise RuntimeError(
            f"database guard mismatch: guard={guard_db}, current={current_db}"
        )

    plan = build_brand_registry_plan(
        strict_payload=_load_json(args.strict_input),
        quality_payload=_load_json(args.quality_input),
        digest_payload=_load_json(args.digest_input),
    )
    async with SessionFactory() as session:
        return cast(
            dict[str, Any],
            await apply_brand_registry_plan(
                session,
                plan,
                database=current_db,
                dry_run=is_dry_run(args),
            ),
        )


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Brand Registry R15.2 Dev Write",
        "",
        f"- DB writes: `{'true' if payload['db_writes'] else 'false'}`",
        f"- target_database: `{payload['database']}`",
        f"- input_registry_rows: `{summary['input_registry_rows']}`",
        f"- input_mentions: `{summary['input_mentions']}`",
        f"- would_insert_registry_rows: `{summary['would_insert_registry_rows']}`",
        f"- would_insert_mentions: `{summary['would_insert_mentions']}`",
        f"- inserted_registry_rows: `{summary['inserted_registry_rows']}`",
        f"- inserted_mentions: `{summary['inserted_mentions']}`",
        f"- rollback_sql: `{payload.get('rollback_sql', '')}`",
        "",
        "## Planned Brand Inserts",
        "",
    ]
    planned = payload.get("planned_insert_brand_keys") or []
    lines.extend(f"- {key}" for key in planned[:120])
    if len(planned) > 120:
        lines.append(f"- ... {len(planned) - 120} more")
    if not planned:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def render_rollback_sql(payload: dict[str, Any]) -> str:
    brand_keys = payload.get("inserted_brand_keys") or []
    mention_keys = payload.get("inserted_mention_keys") or []
    if not payload.get("db_writes"):
        return "-- Dry-run only; no rollback needed.\n"
    if not brand_keys and not mention_keys:
        return "-- No brand registry rows were inserted.\n"
    lines = ["-- Roll back rows inserted by Brand Intelligence R15.2 Dev write."]
    if mention_keys:
        lines.append(
            f"DELETE FROM brand_mentions WHERE mention_key IN ({_sql_values(mention_keys)});"
        )
    if brand_keys:
        lines.append(
            f"DELETE FROM brand_registry WHERE brand_key IN ({_sql_values(brand_keys)});"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write reviewed brands into Dev brand registry."
    )
    parser.add_argument("--strict-input", type=Path, default=DEFAULT_STRICT_INPUT)
    parser.add_argument("--quality-input", type=Path, default=DEFAULT_QUALITY_INPUT)
    parser.add_argument("--digest-input", type=Path, default=DEFAULT_DIGEST_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--rollback-sql", type=Path, default=DEFAULT_ROLLBACK_SQL)
    add_execute_flag(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(build_result_payload(args))
    payload["rollback_sql"] = str(args.rollback_sql)
    rollback_sql = render_rollback_sql(payload)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.md_output.write_text(render_markdown(payload), encoding="utf-8")
    args.rollback_sql.write_text(rollback_sql, encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


def _load_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _sql_values(values: list[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


if __name__ == "__main__":
    main()
