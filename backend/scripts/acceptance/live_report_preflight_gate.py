#!/usr/bin/env python3
from __future__ import annotations

"""
Preflight gate for live report acceptance.

Checks whether queue/backlog noise is within an acceptable range before
running live A_full acceptance.
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


async def _read_backlog_snapshot(stale_minutes: int) -> dict[str, int]:
    async with SessionFactory() as session:
        pending_outbox = int(
            (
                await session.execute(
                    text("SELECT COUNT(*) FROM task_outbox WHERE status = 'pending'")
                )
            ).scalar_one()
        )
        queued_targets = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued'
                        """
                    )
                )
            ).scalar_one()
        )
        queued_not_enqueued = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued'
                          AND enqueued_at IS NULL
                        """
                    )
                )
            ).scalar_one()
        )
        running_targets = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'running'
                        """
                    )
                )
            ).scalar_one()
        )
        stale_pending_outbox = int(
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
        stale_queued_not_enqueued = int(
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
        "task_outbox_pending": pending_outbox,
        "task_outbox_pending_stale": stale_pending_outbox,
        "crawler_run_targets_queued": queued_targets,
        "crawler_run_targets_queued_not_enqueued": queued_not_enqueued,
        "crawler_run_targets_queued_not_enqueued_stale": stale_queued_not_enqueued,
        "crawler_run_targets_running": running_targets,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live report acceptance preflight gate")
    parser.add_argument("--stale-minutes", type=int, default=45)
    parser.add_argument("--max-stale-task-outbox-pending", type=int, default=120)
    parser.add_argument(
        "--max-stale-crawler-targets-not-enqueued", type=int, default=200
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    return parser


async def _main_async() -> int:
    args = _build_parser().parse_args()
    snapshot = await _read_backlog_snapshot(stale_minutes=args.stale_minutes)

    outbox_pending = snapshot["task_outbox_pending"]
    outbox_pending_stale = snapshot["task_outbox_pending_stale"]
    queued_targets = snapshot["crawler_run_targets_queued"]
    queued_not_enqueued = snapshot["crawler_run_targets_queued_not_enqueued"]
    queued_not_enqueued_stale = snapshot[
        "crawler_run_targets_queued_not_enqueued_stale"
    ]
    running_targets = snapshot["crawler_run_targets_running"]

    violations: list[str] = []
    if outbox_pending_stale > args.max_stale_task_outbox_pending:
        violations.append(
            (
                "task_outbox_pending_stale={count} > {max_count} "
                "(window={window}m)"
            ).format(
                count=outbox_pending_stale,
                max_count=args.max_stale_task_outbox_pending,
                window=args.stale_minutes,
            )
        )
    if queued_not_enqueued_stale > args.max_stale_crawler_targets_not_enqueued:
        violations.append(
            (
                "crawler_run_targets_queued_not_enqueued_stale={count} > {max_count} "
                "(window={window}m)"
            ).format(
                count=queued_not_enqueued_stale,
                max_count=args.max_stale_crawler_targets_not_enqueued,
                window=args.stale_minutes,
            )
        )

    payload = {
        "ok": len(violations) == 0,
        "strict": bool(args.strict),
        "thresholds": {
            "stale_minutes": args.stale_minutes,
            "max_stale_task_outbox_pending": args.max_stale_task_outbox_pending,
            "max_stale_crawler_targets_not_enqueued": args.max_stale_crawler_targets_not_enqueued,
        },
        "snapshot": {
            "task_outbox_pending": outbox_pending,
            "task_outbox_pending_stale": outbox_pending_stale,
            "crawler_run_targets_queued": queued_targets,
            "crawler_run_targets_queued_not_enqueued": queued_not_enqueued,
            "crawler_run_targets_queued_not_enqueued_stale": queued_not_enqueued_stale,
            "crawler_run_targets_running": running_targets,
        },
        "violations": violations,
    }

    stream = sys.stderr if (args.strict and violations) else sys.stdout
    if not args.json_only:
        print("==> Live report preflight gate", file=stream)
        print(
            (
                "task_outbox_pending={pending} stale_pending={stale_pending} "
                "queued_targets={queued} queued_not_enqueued={queued_not_enqueued} "
                "stale_queued_not_enqueued={stale_queued_not_enqueued} "
                "running_targets={running}"
            ).format(
                pending=outbox_pending,
                stale_pending=outbox_pending_stale,
                queued=queued_targets,
                queued_not_enqueued=queued_not_enqueued,
                stale_queued_not_enqueued=queued_not_enqueued_stale,
                running=running_targets,
            ),
            file=stream,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)

    if args.strict and violations:
        return 2
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
