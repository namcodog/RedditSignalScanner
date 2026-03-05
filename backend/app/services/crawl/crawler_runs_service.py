from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_CRAWLER_RUNS_TABLE_EXISTS: bool | None = None


async def ensure_crawler_run(
    session: AsyncSession,
    *,
    crawl_run_id: str,
    status: str = "running",
    config: dict[str, Any] | None = None,
) -> None:
    """Create crawler_runs row if the table exists (idempotent).

    This is a best-effort helper to keep inserts into *_crawl_run_id columns safe
    when FK constraints are enabled.
    """
    global _CRAWLER_RUNS_TABLE_EXISTS
    if _CRAWLER_RUNS_TABLE_EXISTS is None:
        exists = (
            await session.execute(text("SELECT to_regclass('public.crawler_runs')"))
        ).scalar_one_or_none()
        _CRAWLER_RUNS_TABLE_EXISTS = bool(exists)

    if not _CRAWLER_RUNS_TABLE_EXISTS:
        return

    payload = json.dumps(config or {})
    await session.execute(
        text(
            """
            INSERT INTO crawler_runs (id, status, config, metrics)
            VALUES (CAST(:id AS uuid), :status, CAST(:config AS jsonb), '{}'::jsonb)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": crawl_run_id, "status": status, "config": payload},
    )


async def complete_crawler_run(
    session: AsyncSession,
    *,
    crawl_run_id: str,
    status: str = "completed",
    metrics: dict[str, Any] | None = None,
) -> None:
    """Mark crawler_runs row as completed (best-effort)."""
    await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
    await session.execute(
        text(
            """
            UPDATE crawler_runs
            SET status = :status,
                completed_at = now(),
                metrics = CAST(:metrics AS jsonb)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": crawl_run_id, "status": status, "metrics": json.dumps(metrics or {})},
    )


__all__ = ["ensure_crawler_run", "complete_crawler_run"]

