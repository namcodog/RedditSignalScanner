from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_CRAWLER_RUN_TARGETS_TABLE_EXISTS: bool | None = None
_CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS: bool | None = None
_CRAWLER_RUN_TARGETS_HAS_DEDUPE_KEY: bool | None = None


async def ensure_crawler_run_target(
    session: AsyncSession,
    *,
    community_run_id: str,
    crawl_run_id: str,
    subreddit: str,
    status: str = "running",
    plan_kind: str | None = None,
    idempotency_key: str | None = None,
    idempotency_key_human: str | None = None,
    dedupe_key: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Create crawler_run_targets row if the table exists (best-effort, idempotent).

    Returns:
        True if a new row was inserted, False if it already existed (conflict) or table missing.
    """
    global _CRAWLER_RUN_TARGETS_TABLE_EXISTS
    if _CRAWLER_RUN_TARGETS_TABLE_EXISTS is None:
        exists = (
            await session.execute(text("SELECT to_regclass('public.crawler_run_targets')"))
        ).scalar_one_or_none()
        _CRAWLER_RUN_TARGETS_TABLE_EXISTS = bool(exists)

    if not _CRAWLER_RUN_TARGETS_TABLE_EXISTS:
        return False

    # Default to idempotency_key when callers don't provide a dedicated dedupe_key.
    if dedupe_key is None and idempotency_key:
        dedupe_key = f"{crawl_run_id}:{idempotency_key}"

    global _CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS
    if _CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS is None:
        cols = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='crawler_run_targets'
                  AND column_name IN ('plan_kind', 'idempotency_key', 'idempotency_key_human')
                """
            )
        )
        existing = {row[0] for row in cols.all()}
        _CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS = (
            "plan_kind" in existing
            and "idempotency_key" in existing
            and "idempotency_key_human" in existing
        )

    global _CRAWLER_RUN_TARGETS_HAS_DEDUPE_KEY
    if _CRAWLER_RUN_TARGETS_HAS_DEDUPE_KEY is None:
        cols = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='crawler_run_targets'
                  AND column_name='dedupe_key'
                """
            )
        )
        _CRAWLER_RUN_TARGETS_HAS_DEDUPE_KEY = bool(cols.scalar_one_or_none())

    payload = json.dumps(config or {})
    if _CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS and _CRAWLER_RUN_TARGETS_HAS_DEDUPE_KEY:
        result = await session.execute(
            text(
                """
                INSERT INTO crawler_run_targets (
                    id, crawl_run_id, subreddit, status, config, metrics,
                    plan_kind, idempotency_key, idempotency_key_human, dedupe_key
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:crawl_run_id AS uuid),
                    :subreddit,
                    :status,
                    CAST(:config AS jsonb),
                    '{}'::jsonb,
                    :plan_kind,
                    :idempotency_key,
                    :idempotency_key_human,
                    :dedupe_key
                )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": community_run_id,
                "crawl_run_id": crawl_run_id,
                "subreddit": subreddit,
                "status": status,
                "config": payload,
                "plan_kind": plan_kind,
                "idempotency_key": idempotency_key,
                "idempotency_key_human": idempotency_key_human,
                "dedupe_key": dedupe_key,
            },
        )
        return bool(getattr(result, "rowcount", 0) or 0)
    elif _CRAWLER_RUN_TARGETS_HAS_PLAN_FIELDS:
        result = await session.execute(
            text(
                """
                INSERT INTO crawler_run_targets (
                    id, crawl_run_id, subreddit, status, config, metrics,
                    plan_kind, idempotency_key, idempotency_key_human
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:crawl_run_id AS uuid),
                    :subreddit,
                    :status,
                    CAST(:config AS jsonb),
                    '{}'::jsonb,
                    :plan_kind,
                    :idempotency_key,
                    :idempotency_key_human
                )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": community_run_id,
                "crawl_run_id": crawl_run_id,
                "subreddit": subreddit,
                "status": status,
                "config": payload,
                "plan_kind": plan_kind,
                "idempotency_key": idempotency_key,
                "idempotency_key_human": idempotency_key_human,
            },
        )
        return bool(getattr(result, "rowcount", 0) or 0)
    else:
        result = await session.execute(
            text(
                """
                INSERT INTO crawler_run_targets (id, crawl_run_id, subreddit, status, config, metrics)
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:crawl_run_id AS uuid),
                    :subreddit,
                    :status,
                    CAST(:config AS jsonb),
                    '{}'::jsonb
                )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": community_run_id,
                "crawl_run_id": crawl_run_id,
                "subreddit": subreddit,
                "status": status,
                "config": payload,
            },
        )
        return bool(getattr(result, "rowcount", 0) or 0)


async def complete_crawler_run_target(
    session: AsyncSession,
    *,
    community_run_id: str,
    status: str = "completed",
    metrics: dict[str, Any] | None = None,
) -> None:
    """Mark crawler_run_targets row as completed (best-effort)."""
    global _CRAWLER_RUN_TARGETS_TABLE_EXISTS
    if _CRAWLER_RUN_TARGETS_TABLE_EXISTS is False:
        return

    await session.execute(
        text(
            """
            UPDATE crawler_run_targets
            SET status = :status,
                completed_at = now(),
                metrics = CAST(:metrics AS jsonb)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {
            "id": community_run_id,
            "status": status,
            "metrics": json.dumps(metrics or {}),
        },
    )


async def fail_crawler_run_target(
    session: AsyncSession,
    *,
    community_run_id: str,
    error_code: str = "failed",
    error_message_short: str | None = None,
) -> None:
    """Mark crawler_run_targets row as failed (best-effort)."""
    global _CRAWLER_RUN_TARGETS_TABLE_EXISTS
    if _CRAWLER_RUN_TARGETS_TABLE_EXISTS is False:
        return

    await session.execute(
        text(
            """
            UPDATE crawler_run_targets
            SET status = 'failed',
                completed_at = now(),
                error_code = :error_code,
                error_message_short = :error_message_short
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {
            "id": community_run_id,
            "error_code": error_code,
            "error_message_short": error_message_short,
        },
    )


async def partial_crawler_run_target(
    session: AsyncSession,
    *,
    community_run_id: str,
    error_code: str = "partial",
    error_message_short: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    """Mark crawler_run_targets row as partial (best-effort)."""
    global _CRAWLER_RUN_TARGETS_TABLE_EXISTS
    if _CRAWLER_RUN_TARGETS_TABLE_EXISTS is False:
        return

    await session.execute(
        text(
            """
            UPDATE crawler_run_targets
            SET status = 'partial',
                completed_at = now(),
                error_code = :error_code,
                error_message_short = :error_message_short,
                metrics = CAST(:metrics AS jsonb)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {
            "id": community_run_id,
            "error_code": error_code,
            "error_message_short": error_message_short,
            "metrics": json.dumps(metrics or {}),
        },
    )


__all__ = [
    "ensure_crawler_run_target",
    "complete_crawler_run_target",
    "fail_crawler_run_target",
    "partial_crawler_run_target",
]
