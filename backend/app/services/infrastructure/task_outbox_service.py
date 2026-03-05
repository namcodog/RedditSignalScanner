from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import DATABASE_URL


OUTBOX_EVENT_EXECUTE_TARGET = "execute_target"

_TASK_OUTBOX_TABLE_EXISTS: bool | None = None
_OUTBOX_ENV_FINGERPRINT: str | None = None

logger = logging.getLogger(__name__)


def build_task_outbox_event_key(*, event_type: str, target_id: str) -> str:
    return f"{event_type}:{target_id}"


def resolve_outbox_env_fingerprint() -> str:
    global _OUTBOX_ENV_FINGERPRINT
    if _OUTBOX_ENV_FINGERPRINT is None:
        override = os.getenv("OUTBOX_ENV_FINGERPRINT", "").strip()
        if override:
            _OUTBOX_ENV_FINGERPRINT = override
        else:
            url = make_url(DATABASE_URL)
            host = url.host or "unknown-host"
            dbname = url.database or "unknown-db"
            _OUTBOX_ENV_FINGERPRINT = f"{host}:{dbname}"
    return _OUTBOX_ENV_FINGERPRINT


async def _task_outbox_table_exists(session: AsyncSession) -> bool:
    global _TASK_OUTBOX_TABLE_EXISTS
    if _TASK_OUTBOX_TABLE_EXISTS is None:
        exists = (
            await session.execute(text("SELECT to_regclass('public.task_outbox')"))
        ).scalar_one_or_none()
        if exists:
            _TASK_OUTBOX_TABLE_EXISTS = True
            return True
        try:
            current_db = await session.scalar(text("SELECT current_database()"))
        except Exception:
            current_db = "unknown-db"
        logger.warning(
            "task_outbox 表不存在或不可见 (db=%s fingerprint=%s)",
            current_db,
            resolve_outbox_env_fingerprint(),
        )
        return False
    return True


async def ensure_task_outbox_event(
    session: AsyncSession,
    *,
    event_key: str,
    event_type: str,
    payload: dict[str, Any] | None,
) -> bool:
    if not await _task_outbox_table_exists(session):
        return False

    payload_json = json.dumps(payload or {})
    result = await session.execute(
        text(
            """
            INSERT INTO task_outbox (
                id, event_key, event_type, payload, status, retry_count
            )
            VALUES (
                CAST(:id AS uuid),
                :event_key,
                :event_type,
                CAST(:payload AS jsonb),
                'pending',
                0
            )
            ON CONFLICT (event_key) DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "event_key": event_key,
            "event_type": event_type,
            "payload": payload_json,
        },
    )
    return bool(getattr(result, "rowcount", 0) or 0)


async def enqueue_execute_target_outbox(
    session: AsyncSession,
    *,
    target_id: str,
    queue: str,
    countdown: int | None = None,
) -> bool:
    payload: dict[str, Any] = {"target_id": target_id, "queue": queue}
    payload["env_fingerprint"] = resolve_outbox_env_fingerprint()
    if countdown:
        payload["countdown"] = int(countdown)
    event_key = build_task_outbox_event_key(
        event_type=OUTBOX_EVENT_EXECUTE_TARGET, target_id=target_id
    )
    return await ensure_task_outbox_event(
        session,
        event_key=event_key,
        event_type=OUTBOX_EVENT_EXECUTE_TARGET,
        payload=payload,
    )


async def fetch_pending_task_outbox(
    session: AsyncSession, *, limit: int
) -> list[dict[str, Any]]:
    if not await _task_outbox_table_exists(session):
        return []

    rows = await session.execute(
        text(
            """
            SELECT id, event_key, event_type, payload, retry_count
            FROM task_outbox
            WHERE status = 'pending'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(row) for row in rows.mappings().all()]


async def mark_task_outbox_sent(
    session: AsyncSession,
    *,
    outbox_id: str,
    note: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE task_outbox
            SET status = 'sent',
                sent_at = now(),
                last_error = :note
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": outbox_id, "note": note},
    )


async def mark_task_outbox_failed(
    session: AsyncSession,
    *,
    outbox_id: str,
    error: str,
    max_retries: int,
) -> str:
    row = await session.execute(
        text(
            """
            UPDATE task_outbox
            SET retry_count = retry_count + 1,
                last_error = :error,
                status = CASE
                    WHEN (retry_count + 1) >= :max_retries THEN 'failed'
                    ELSE 'pending'
                END
            WHERE id = CAST(:id AS uuid)
            RETURNING status
            """
        ),
        {"id": outbox_id, "error": error, "max_retries": max_retries},
    )
    return str(row.scalar_one_or_none() or "pending")
