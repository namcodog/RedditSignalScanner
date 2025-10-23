from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskStatsResponse, TaskStatusSnapshot
from app.services.task_status_cache import TaskStatusCache, TaskStatusPayload

status_router = APIRouter(prefix="/status", tags=["status"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
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


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc


@status_router.get(
    "/{task_id}",
    response_model=TaskStatusSnapshot,
    summary="获取任务状态（缓存优先）",
)
async def get_task_status(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),  # noqa: ARG001 - reserved for SSE URLs
) -> TaskStatusSnapshot:
    user_uuid = _parse_uuid(payload.sub)

    task: Task | None = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this task",
        )

    cached = await STATUS_CACHE.get_status(str(task_id), session=db)

    # 若缓存存在但与数据库中的终态不一致（completed/failed），以数据库为准并回填缓存，避免陈旧状态
    if cached is not None:
        cached_status = TaskStatus(cached.status)
        db_status = task.status
        if db_status in {TaskStatus.COMPLETED, TaskStatus.FAILED} and cached_status != db_status:
            status_value = db_status
            progress = _PROGRESS_MAP.get(status_value, 0)
            message = _MESSAGE_MAP.get(status_value, "")
            error = task.error_message
            updated_at = task.updated_at or datetime.now(timezone.utc)
            # 异步地回填缓存（不阻塞请求）
            try:
                await STATUS_CACHE.set_status(
                    TaskStatusPayload(
                        task_id=str(task.id),
                        status=status_value.value,
                        progress=progress,
                        message=message,
                        error=error,
                        updated_at=updated_at.isoformat(),
                    )
                )
            except Exception:
                pass
        else:
            status_value = cached_status
            updated_at = (
                datetime.fromisoformat(cached.updated_at)
                if cached.updated_at
                else datetime.now(timezone.utc)
            )
            progress = cached.progress
            message = cached.message or _MESSAGE_MAP.get(status_value, "")
            error = cached.error or task.error_message
    else:
        status_value = task.status
        progress = _PROGRESS_MAP.get(status_value, 0)
        message = _MESSAGE_MAP.get(status_value, "")
        error = task.error_message
        updated_at = task.updated_at or datetime.now(timezone.utc)

    return TaskStatusSnapshot(
        task_id=task.id,
        status=status_value,
        progress=progress,
        message=message,
        error=error,
        percentage=progress,
        current_step=message or "",
        sse_endpoint=f"{settings.sse_base_path}/{task.id}",
        retry_count=task.retry_count,
        failure_category=task.failure_category,
        last_retry_at=task.last_retry_at,
        dead_letter_at=task.dead_letter_at,
        updated_at=updated_at,
    )


@tasks_router.get(
    "/stats",
    response_model=TaskStatsResponse,
    summary="获取任务队列统计信息",
)
async def get_task_stats(
    _payload: TokenPayload = Depends(decode_jwt_token),
) -> TaskStatsResponse:
    """
    Return aggregate Celery worker statistics to support operational dashboards.
    """

    inspect = celery_app.control.inspect()
    if inspect is None:
        return TaskStatsResponse(
            active_workers=0,
            active_tasks=0,
            reserved_tasks=0,
            scheduled_tasks=0,
            total_tasks=0,
        )

    active_workers = inspect.active() or {}
    reserved_tasks = inspect.reserved() or {}
    scheduled_tasks = inspect.scheduled() or {}

    total_active_tasks = sum(len(tasks) for tasks in active_workers.values())
    total_reserved_tasks = sum(len(tasks) for tasks in reserved_tasks.values())
    total_scheduled_tasks = sum(len(tasks) for tasks in scheduled_tasks.values())

    return TaskStatsResponse(
        active_workers=len(active_workers),
        active_tasks=total_active_tasks,
        reserved_tasks=total_reserved_tasks,
        scheduled_tasks=total_scheduled_tasks,
        total_tasks=total_active_tasks + total_reserved_tasks + total_scheduled_tasks,
    )


router = status_router

__all__ = ["status_router", "tasks_router", "router"]


# 运行时诊断：返回关键配置是否就绪（不泄露机密）
@tasks_router.get("/diag", summary="运行时配置诊断")
async def tasks_diag() -> dict[str, str | bool]:
    s = get_settings()
    return {
        "has_reddit_client": bool(s.reddit_client_id and s.reddit_client_secret),
        "environment": s.environment,
    }
