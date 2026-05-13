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
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionFactory
from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.community_pool_feedback_dry_run import (
    build_pool_feedback_dry_run,
    load_active_pool_community_keys,
)
from app.services.hotpost.community_pool_feedback_markdown import render_pool_feedback_markdown

DEFAULT_INPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-discovery-audit-{date.today().isoformat()}.json"
)
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-pool-feedback-dry-run-{date.today().isoformat()}.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT
    / "reports"
    / "community-governance"
    / f"community-pool-feedback-dry-run-{date.today().isoformat()}.md"
)


async def build(input_path: Path) -> dict[str, object]:
    audit_payload = json.loads(input_path.read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        pool_keys = await load_active_pool_community_keys(session)
    return build_pool_feedback_dry_run(audit_payload, pool_community_keys=pool_keys)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Hotpost community pool feedback dry-run reports.")
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
    args.md_output.write_text(render_pool_feedback_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
