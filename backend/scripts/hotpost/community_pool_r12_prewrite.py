from __future__ import annotations

import argparse
import asyncio
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.community_pool_r12_markdown import render_r12_prewrite_markdown
from app.services.hotpost.community_pool_r12_prewrite import build_r12_prewrite_plan

DEFAULT_INPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-pool-feedback-dry-run-{date.today().isoformat()}.json"
)
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-pool-r12-prewrite-{date.today().isoformat()}.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-pool-r12-prewrite-{date.today().isoformat()}.md"
)


async def _pool_key_sets() -> tuple[set[str], set[str]]:
    async with SessionFactory() as session:
        result = await session.execute(select(CommunityPool.name_key, CommunityPool.deleted_at))
    active: set[str] = set()
    deleted: set[str] = set()
    for name_key, deleted_at in result.all():
        if deleted_at is None:
            active.add(str(name_key))
        else:
            deleted.add(str(name_key))
    return active, deleted


async def build(input_path: Path) -> dict[str, Any]:
    feedback_payload = json.loads(input_path.read_text(encoding="utf-8"))
    active_keys, deleted_keys = await _pool_key_sets()
    return build_r12_prewrite_plan(
        feedback_payload,
        active_pool_keys=active_keys,
        deleted_pool_keys=deleted_keys,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Hotpost community pool R12 prewrite audit.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    return parser.parse_args()


def main() -> None:
    load_backend_env()
    args = parse_args()
    payload = asyncio.run(build(args.input))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.md_output.write_text(render_r12_prewrite_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
