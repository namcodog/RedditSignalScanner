from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.infrastructure.task_outbox_service import (
    fetch_pending_task_outbox,
    mark_task_outbox_failed,
    mark_task_outbox_sent,
    resolve_outbox_env_fingerprint,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TaskOutboxDispatchResult:
    status: str
    selected: int
    sent: int
    skipped: int
    failed: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "status": self.status,
            "selected": self.selected,
            "sent": self.sent,
            "skipped": self.skipped,
            "failed": self.failed,
        }


def _summarize_dispatch_status(*, selected: int, sent: int, skipped: int, failed: int) -> str:
    if selected <= 0:
        return "idle"
    if sent > 0 and failed == 0:
        return "completed"
    if sent > 0:
        return "degraded"
    return "failed"


def _normalize_outbox_payload(raw_payload: Any) -> dict[str, Any]:
    if isinstance(raw_payload, Mapping):
        return dict(raw_payload)
    return {}


async def dispatch_pending_task_outbox(
    session: AsyncSession,
    *,
    batch_size: int,
    max_retries: int,
    send_task: Callable[..., Any],
    execute_task_name: str,
    comments_backfill_queue: str,
    backfill_posts_queue: str,
) -> TaskOutboxDispatchResult:
    sent = 0
    skipped = 0
    failed = 0
    expected_fingerprint = resolve_outbox_env_fingerprint()

    try:
        current_db = await session.scalar(text("SELECT current_database()"))
    except Exception:
        current_db = "unknown-db"

    rows = await fetch_pending_task_outbox(session, limit=batch_size)
    if not rows:
        logger.info(
            "task_outbox 派发 idle (db=%s fingerprint=%s)",
            current_db,
            expected_fingerprint,
        )
        return TaskOutboxDispatchResult(
            status="idle",
            selected=0,
            sent=0,
            skipped=0,
            failed=0,
        )

    logger.info(
        "task_outbox 派发选取=%s (db=%s fingerprint=%s)",
        len(rows),
        current_db,
        expected_fingerprint,
    )

    for row in rows:
        outbox_id = str(row.get("id") or "")
        payload = _normalize_outbox_payload(row.get("payload"))
        target_id = str(payload.get("target_id") or "")
        queue = str(payload.get("queue") or comments_backfill_queue)
        countdown = payload.get("countdown")
        payload_fingerprint = str(payload.get("env_fingerprint") or "")

        if not outbox_id:
            failed += 1
            continue

        if not target_id:
            await mark_task_outbox_failed(
                session,
                outbox_id=outbox_id,
                error="missing_target_id",
                max_retries=max_retries,
            )
            failed += 1
            continue

        if payload_fingerprint and payload_fingerprint != expected_fingerprint:
            await mark_task_outbox_failed(
                session,
                outbox_id=outbox_id,
                error=f"env_fingerprint_mismatch:{payload_fingerprint}",
                max_retries=max_retries,
            )
            logger.warning(
                "task_outbox 指纹不一致 (payload=%s expected=%s)",
                payload_fingerprint,
                expected_fingerprint,
            )
            failed += 1
            continue

        target_row = await session.execute(
            text(
                """
                SELECT enqueued_at, plan_kind
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        target_record = target_row.mappings().first()
        if target_record is None:
            await mark_task_outbox_failed(
                session,
                outbox_id=outbox_id,
                error="target_missing",
                max_retries=max_retries,
            )
            failed += 1
            continue

        enqueued_at = target_record.get("enqueued_at")
        plan_kind = str(target_record.get("plan_kind") or "")
        if enqueued_at is not None:
            await mark_task_outbox_sent(
                session,
                outbox_id=outbox_id,
                note="already_enqueued",
            )
            skipped += 1
            continue

        if plan_kind == "backfill_posts":
            queue = backfill_posts_queue

        try:
            send_kwargs: dict[str, Any] = {
                "kwargs": {"target_id": target_id},
                "queue": queue,
            }
            if countdown:
                send_kwargs["countdown"] = int(countdown)
            send_task(execute_task_name, **send_kwargs)

            await session.execute(
                text(
                    """
                    UPDATE crawler_run_targets
                    SET enqueued_at = now()
                    WHERE id = CAST(:id AS uuid)
                      AND enqueued_at IS NULL
                    """
                ),
                {"id": target_id},
            )
            await mark_task_outbox_sent(session, outbox_id=outbox_id)
            sent += 1
        except Exception as exc:
            await mark_task_outbox_failed(
                session,
                outbox_id=outbox_id,
                error=str(exc)[:400],
                max_retries=max_retries,
            )
            failed += 1

    return TaskOutboxDispatchResult(
        status=_summarize_dispatch_status(
            selected=len(rows),
            sent=sent,
            skipped=skipped,
            failed=failed,
        ),
        selected=len(rows),
        sent=sent,
        skipped=skipped,
        failed=failed,
    )


__all__ = ["TaskOutboxDispatchResult", "dispatch_pending_task_outbox"]
