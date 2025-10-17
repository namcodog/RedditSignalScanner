from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from time import monotonic
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.task import Task, TaskStatus
from app.services.task_status_cache import TaskStatusCache, TaskStatusPayload

POLL_INTERVAL_SECONDS = float(os.getenv("TASK_STREAM_POLL_INTERVAL", "1.0"))
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("TASK_STREAM_HEARTBEAT_INTERVAL", "30.0"))

router = APIRouter(prefix="/analyze", tags=["analysis"])
STATUS_CACHE = TaskStatusCache()

_PROGRESS_MAP: dict[TaskStatus, int] = {
    TaskStatus.PENDING: 0,
    TaskStatus.PROCESSING: 50,
    TaskStatus.COMPLETED: 100,
    TaskStatus.FAILED: 0,
}

_MESSAGE_MAP: dict[TaskStatus, str] = {
    TaskStatus.PENDING: "任务排队中",
    TaskStatus.PROCESSING: "任务正在处理",
    TaskStatus.COMPLETED: "分析完成",
    TaskStatus.FAILED: "任务失败",
}


def _format_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _payload_to_dict(payload: TaskStatusPayload) -> dict[str, object]:
    return {
        "task_id": payload.task_id,
        "status": payload.status,
        "progress": payload.progress,
        "message": payload.message,
        "error": payload.error,
        "updated_at": payload.updated_at,
    }


def _resolve_event_name(status_value: str) -> str:
    if status_value == TaskStatus.COMPLETED.value:
        return "completed"
    if status_value == TaskStatus.FAILED.value:
        return "error"
    return "progress"


def _task_to_payload(task: Task) -> TaskStatusPayload:
    status_value = task.status
    status_message = _MESSAGE_MAP.get(status_value, "")
    updated_at = (task.updated_at or datetime.now(timezone.utc)).isoformat()
    return TaskStatusPayload(
        task_id=str(task.id),
        status=status_value.value,
        progress=_PROGRESS_MAP.get(status_value, 0),
        message=status_message,
        error=task.error_message,
        updated_at=updated_at,
    )


async def _event_generator(
    task: Task,
    db: AsyncSession,
) -> AsyncIterator[str]:
    task_id_str = str(task.id)
    baseline_payload = _task_to_payload(task)
    last_signature: str | None = None
    last_heartbeat = monotonic()

    yield _format_event("connected", {"task_id": task_id_str})

    baseline_event = _resolve_event_name(baseline_payload.status)
    baseline_data = _payload_to_dict(baseline_payload)
    yield _format_event(baseline_event, baseline_data)
    last_signature = baseline_payload.encode()

    if baseline_event in {"completed", "error"}:
        yield _format_event("close", {"task_id": task_id_str})
        return

    while True:
        try:
            payload = await STATUS_CACHE.get_status(task_id_str, session=db)
            if payload is not None:
                signature = payload.encode()
                if signature != last_signature:
                    event_name = _resolve_event_name(payload.status)
                    yield _format_event(event_name, _payload_to_dict(payload))
                    last_signature = signature
                    last_heartbeat = monotonic()
                    if event_name in {"completed", "error"}:
                        yield _format_event("close", {"task_id": task_id_str})
                        return

            now = monotonic()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                last_heartbeat = now
                yield _format_event(
                    "heartbeat",
                    {
                        "task_id": task_id_str,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise


@router.get("/stream/{task_id}", summary="Task streaming progress (SSE)")  # type: ignore[misc]
async def stream_task_progress(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(
        get_settings
    ),  # noqa: ARG001 - reserved for SSE base path usage
) -> StreamingResponse:
    task: Task | None = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if str(task.user_id) != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this task",
        )

    generator = _event_generator(task, db)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


__all__ = ["router"]
