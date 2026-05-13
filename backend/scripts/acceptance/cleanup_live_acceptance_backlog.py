#!/usr/bin/env python3
from __future__ import annotations

"""
Clean stale backlog noise before live report acceptance (dev-only workflow).

This utility is intentionally conservative:
- Only affects stale `task_outbox(status=pending)` rows.
- Only affects stale `crawler_run_targets(status=queued)` rows.
- Defaults to dry-run unless `--apply` is explicitly passed.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cleanup stale live-acceptance backlog")
    parser.add_argument("--stale-minutes", type=int, default=45)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--apply", action="store_true")
    return parser


async def _count_candidates(stale_minutes: int) -> dict[str, int]:
    async with SessionFactory() as session:
        outbox_count = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM task_outbox
                        WHERE status = 'pending'
                          AND created_at < now() - make_interval(mins => :stale_minutes)
                        """
                    ),
                    {"stale_minutes": stale_minutes},
                )
            ).scalar_one()
        )
        queued_count = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued'
                          AND enqueued_at IS NULL
                          AND started_at < now() - make_interval(mins => :stale_minutes)
                        """
                    ),
                    {"stale_minutes": stale_minutes},
                )
            ).scalar_one()
        )
    return {
        "stale_task_outbox_pending": outbox_count,
        "stale_crawler_targets_queued": queued_count,
    }


async def _apply_cleanup(stale_minutes: int, batch_size: int) -> dict[str, int]:
    batch_size = max(1, int(batch_size))
    outbox_updated_total = 0
    targets_updated_total = 0

    async with SessionFactory() as session:
        # Avoid lock waits by only touching unlocked rows in small batches.
        while True:
            async with session.begin():
                outbox_updated = (
                    await session.execute(
                        text(
                            """
                            WITH stale AS (
                                SELECT id
                                FROM task_outbox
                                WHERE status = 'pending'
                                  AND created_at < now() - make_interval(mins => :stale_minutes)
                                FOR UPDATE SKIP LOCKED
                                LIMIT :batch_size
                            )
                            UPDATE task_outbox o
                            SET status = 'failed',
                                retry_count = o.retry_count + 1,
                                last_error = :reason,
                                sent_at = now()
                            WHERE o.id IN (SELECT id FROM stale)
                            """
                        ),
                        {
                            "stale_minutes": stale_minutes,
                            "batch_size": batch_size,
                            "reason": "acceptance_preflight_cleanup_stale_pending",
                        },
                    )
                ).rowcount or 0
                targets_updated = (
                    await session.execute(
                        text(
                            """
                            WITH stale AS (
                                SELECT id
                                FROM crawler_run_targets
                                WHERE status = 'queued'
                                  AND enqueued_at IS NULL
                                  AND started_at < now() - make_interval(mins => :stale_minutes)
                                FOR UPDATE SKIP LOCKED
                                LIMIT :batch_size
                            )
                            UPDATE crawler_run_targets t
                            SET status = 'failed',
                                completed_at = now(),
                                error_code = :error_code,
                                error_message_short = :error_message
                            WHERE t.id IN (SELECT id FROM stale)
                            """
                        ),
                        {
                            "stale_minutes": stale_minutes,
                            "batch_size": batch_size,
                            "error_code": "acceptance_cleanup",
                            "error_message": "stale queued target cleaned before live acceptance",
                        },
                    )
                ).rowcount or 0

            outbox_updated_total += int(outbox_updated)
            targets_updated_total += int(targets_updated)
            if outbox_updated < batch_size and targets_updated < batch_size:
                break

    return {
        "task_outbox_pending_marked_failed": int(outbox_updated_total),
        "crawler_targets_queued_marked_failed": int(targets_updated_total),
    }


async def _main_async() -> int:
    args = _parser().parse_args()
    candidates = await _count_candidates(args.stale_minutes)

    payload: dict[str, object] = {
        "stale_minutes": int(args.stale_minutes),
        "apply": bool(args.apply),
        "candidates": candidates,
    }

    if args.apply:
        payload["updated"] = await _apply_cleanup(
            stale_minutes=args.stale_minutes,
            batch_size=args.batch_size,
        )
        payload["after"] = await _count_candidates(args.stale_minutes)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
