from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.celery_app import celery_app
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models import Analysis, Task, TaskStatus, User

router = APIRouter(prefix="/admin", tags=["admin"])


def _response(data: Any) -> dict[str, Any]:
    return {"code": 0, "data": data, "trace_id": uuid.uuid4().hex}


def _calculate_processing_seconds(task: Task) -> float | None:
    if task.started_at is None or task.completed_at is None:
        return None
    delta = task.completed_at - task.started_at
    return float(round(delta.total_seconds(), 2))


def _collect_worker_count() -> int:
    inspect = celery_app.control.inspect()
    if inspect is None:
        return 0

    active = inspect.active() or {}
    return len(active)


@router.get("/dashboard/stats", summary="Admin dashboard aggregate metrics")  # type: ignore[misc]
async def get_dashboard_stats(
    _payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_tasks = await db.scalar(select(func.count(Task.id))) or 0
    tasks_today = (
        await db.scalar(
            select(func.count(Task.id)).where(Task.created_at >= today_start)
        )
    ) or 0
    tasks_completed_today = (
        await db.scalar(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= today_start,
            )
        )
    ) or 0

    processing_avg_seconds = await db.scalar(
        select(
            func.avg(func.extract("epoch", Task.completed_at - Task.started_at))
        ).where(Task.completed_at.is_not(None), Task.started_at.is_not(None))
    )

    avg_processing_time = round(float(processing_avg_seconds or 0.0), 2)

    cache_hit_avg = await db.scalar(
        select(func.avg(Analysis.sources["cache_hit_rate"].astext.cast(Float)))
    )
    cache_hit_rate = round(float(cache_hit_avg or 0.0), 2)

    stats = {
        "total_users": int(total_users),
        "total_tasks": int(total_tasks),
        "tasks_today": int(tasks_today),
        "tasks_completed_today": int(tasks_completed_today),
        "avg_processing_time": avg_processing_time,
        "cache_hit_rate": cache_hit_rate,
        "active_workers": _collect_worker_count(),
    }

    return _response(stats)


@router.get("/tasks/recent", summary="Recent tasks overview")  # type: ignore[misc]
async def get_recent_tasks(
    _payload: TokenPayload = Depends(require_admin),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = (
        select(Task, User.email)
        .join(User, User.id == Task.user_id)
        .order_by(desc(Task.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for task, email in rows:
        items.append(
            {
                "task_id": task.id,
                "user_email": email,
                "status": task.status.value
                if isinstance(task.status, TaskStatus)
                else task.status,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "processing_seconds": _calculate_processing_seconds(task),
            }
        )

    return _response({"items": items, "total": len(items)})


@router.get("/users/active", summary="Active users ranked by recent tasks")  # type: ignore[misc]
async def get_active_users(
    _payload: TokenPayload = Depends(require_admin),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    threshold = datetime.now(timezone.utc) - timedelta(days=7)

    stmt = (
        select(
            User.id,
            User.email,
            func.count(Task.id).label("task_count"),
            func.max(Task.created_at).label("last_task_at"),
        )
        .join(Task, Task.user_id == User.id)
        .where(Task.created_at >= threshold)
        .group_by(User.id, User.email)
        .order_by(desc("task_count"), desc("last_task_at"))
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()
    items = [
        {
            "user_id": row.id,
            "email": row.email,
            "tasks_last_7_days": int(row.task_count),
            "last_task_at": row.last_task_at,
        }
        for row in rows
    ]

    return _response({"items": items, "total": len(items)})


__all__ = ["router"]
