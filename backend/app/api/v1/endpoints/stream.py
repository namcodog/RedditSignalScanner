from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.task import Task
from app.services.infrastructure.task_status_cache import TaskStatusCache, TaskStatusPayload

# Reuse legacy stream module so monkeypatches in tests stay in effect
from app.api.routes import stream as legacy_stream

POLL_INTERVAL_SECONDS = float(os.getenv("TASK_STREAM_POLL_INTERVAL", "1.0"))
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("TASK_STREAM_HEARTBEAT_INTERVAL", "30.0"))

router = APIRouter()


@router.get(
    "/analyze/stream/{task_id}",
    summary="Task streaming progress (SSE)",
    responses={
        200: {
            "description": "SSE Stream",
            "content": {"text/event-stream": {}}
        }
    }
)
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

    # Delegate to legacy stream generator to keep behavior identical and monkeypatchable
    generator = legacy_stream._event_generator(task, db)  # type: ignore[attr-defined]
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
