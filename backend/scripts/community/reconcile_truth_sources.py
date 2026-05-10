#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory
from app.services.community.truth_source_batch_service import (
    reconcile_legacy_truth_batch,
    reconcile_single_community_name,
)


def _parse_names(raw_names: list[str]) -> list[str]:
    names: list[str] = []
    for raw in raw_names:
        for item in raw.split(","):
            normalized = item.strip()
            if normalized:
                names.append(normalized)
    return names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile legacy community_pool/community_cache into truth-source tables.",
    )
    parser.add_argument(
        "--community",
        action="append",
        default=[],
        help="指定社区名，支持重复传入或逗号分隔；不传则按 batch 模式扫描。",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    return parser


def _single_result_payload(result: Any) -> dict[str, Any]:
    if result is None:
        return {"found": False}
    return {
        "found": True,
        "community_name": result.community_name,
        "registry_id": result.registry_id,
        "memberships_written": result.memberships_written,
        "governance_written": result.governance_written,
        "runtime_state_written": result.runtime_state_written,
    }


async def _main_async() -> int:
    args = _build_parser().parse_args()
    community_names = _parse_names(args.community)

    async with SessionFactory() as session:
        if len(community_names) == 1:
            result = await reconcile_single_community_name(
                session,
                community_name=community_names[0],
                dry_run=args.dry_run,
            )
            payload = {
                "mode": "single",
                "dry_run": args.dry_run,
                "result": _single_result_payload(result),
            }
        else:
            result = await reconcile_legacy_truth_batch(
                session,
                include_inactive=args.include_inactive,
                limit=args.limit,
                dry_run=args.dry_run,
                community_names=community_names or None,
            )
            payload = {
                "mode": "batch",
                "dry_run": args.dry_run,
                "community_filter": community_names,
                "result": {
                    "scanned": result.scanned,
                    "synced": result.synced,
                    "skipped": result.skipped,
                },
            }

    if not args.json_only:
        print("==> truth-source reconciliation")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
