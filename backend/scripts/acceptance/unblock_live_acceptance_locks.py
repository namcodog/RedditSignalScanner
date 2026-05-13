#!/usr/bin/env python3
from __future__ import annotations

"""
Detect and optionally terminate stale lock blockers for live acceptance.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unblock stale DB lock sessions for live acceptance")
    parser.add_argument("--idle-in-tx-seconds", type=int, default=60)
    parser.add_argument("--lock-wait-seconds", type=int, default=120)
    parser.add_argument("--apply", action="store_true")
    return parser


async def _find_blockers(idle_in_tx_seconds: int, lock_wait_seconds: int) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT
            pid,
            usename,
            application_name,
            state,
            wait_event_type,
            wait_event,
            EXTRACT(EPOCH FROM (now() - COALESCE(query_start, state_change)))::bigint AS age_seconds,
            LEFT(query, 240) AS query
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND pid <> pg_backend_pid()
          AND (
            (state = 'idle in transaction'
             AND now() - state_change > make_interval(secs => :idle_in_tx_seconds))
            OR
            (wait_event_type = 'Lock'
             AND now() - query_start > make_interval(secs => :lock_wait_seconds))
          )
        ORDER BY age_seconds DESC
        """
    )

    async with SessionFactory() as session:
        rows = (await session.execute(
            sql,
            {
                "idle_in_tx_seconds": idle_in_tx_seconds,
                "lock_wait_seconds": lock_wait_seconds,
            },
        )).mappings().all()
    return [dict(row) for row in rows]


async def _terminate_blockers(pids: list[int]) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        terminated: list[dict[str, Any]] = []
        for pid in pids:
            ok = bool(
                (
                    await session.execute(
                        text("SELECT pg_terminate_backend(:pid)"), {"pid": int(pid)}
                    )
                ).scalar_one()
            )
            terminated.append({"pid": int(pid), "terminated": ok})
        await session.commit()
    return terminated


async def _main_async() -> int:
    args = _parser().parse_args()
    blockers = await _find_blockers(
        idle_in_tx_seconds=args.idle_in_tx_seconds,
        lock_wait_seconds=args.lock_wait_seconds,
    )
    payload: dict[str, Any] = {
        "apply": bool(args.apply),
        "thresholds": {
            "idle_in_tx_seconds": int(args.idle_in_tx_seconds),
            "lock_wait_seconds": int(args.lock_wait_seconds),
        },
        "blockers": blockers,
    }
    if args.apply and blockers:
        payload["terminated"] = await _terminate_blockers([int(item["pid"]) for item in blockers])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
