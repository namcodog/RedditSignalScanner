from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskCreateResponse
from app.tasks.analysis_task import execute_analysis_pipeline

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _schedule_analysis(
    task_id: uuid.UUID,
    settings: Settings,
    *,
    user_id: uuid.UUID | None = None,
) -> None:
    """
    Dispatch the analysis job to Celery; fallback to inline execution in dev/test.
    """
    # RLS 需要：分析链路（worker/inline）必须带上 user_id，保证写 analyses/reports 不会被 RLS 拦掉。

    async def _get_task_user_id(task_uuid: uuid.UUID) -> uuid.UUID | None:
        from sqlalchemy import select
        from app.models.task import Task as TaskModel
        from app.db.session import get_session_context

        async with get_session_context() as session:
            result = await session.execute(
                select(TaskModel.user_id).where(TaskModel.id == task_uuid)
            )
            row = result.first()
            return row[0] if row else None

    # 优先使用调用方传入的 user_id；否则从 task 表补一手（task 表不依赖 current_user_id，可安全读取）。
    if user_id is None:
        try:
            user_id = await _get_task_user_id(task_id)
        except Exception:
            user_id = None

    inline_preferred = settings.environment.lower() in {
        "development",
        "test",
    } and os.getenv("ENABLE_CELERY_DISPATCH", "1").lower() not in {"1", "true", "yes"}

    if inline_preferred:
        # 在测试环境直接使用当前事件循环执行，避免跨 loop Future 绑定问题
        if settings.environment.lower() == "test":
            logger.info(
                "Environment %s executing analysis task %s inline on request loop (test-safe).",
                settings.environment,
                task_id,
            )
            try:
                await execute_analysis_pipeline(task_id, user_id=user_id)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                logger.exception("Inline analysis task %s failed: %s", task_id, exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Analysis failed",
                ) from exc
            return

        logger.info(
            "Environment %s scheduling analysis task %s inline (Celery bypass for local/dev).",
            settings.environment,
            task_id,
        )
        # 直接在当前 loop 异步执行，避免在 executor 里跨 loop 绑定 Future 引发 500/假死
        asyncio.create_task(execute_analysis_pipeline(task_id, user_id=user_id))
        return

    try:
        args = [str(task_id), str(user_id)] if user_id is not None else [str(task_id)]
        sent = celery_app.send_task("tasks.analysis.run", args=args)
        logger.info("Dispatched analysis task %s to Celery (id=%s).", task_id, sent.id)
    except Exception as exc:  # pragma: no cover - depends on runtime availability
        if settings.environment.lower() in {"development", "test"}:
            logger.warning(
                "Celery dispatch failed for task %s; falling back to inline execution. Error: %s",
                task_id,
                exc,
            )
            loop = asyncio.get_running_loop()
            loop.create_task(execute_analysis_pipeline(task_id, user_id=user_id))
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis queue unavailable, please retry later.",
        ) from exc


@router.post(
    "/analyze",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskCreateResponse,
    summary="Create analysis task",
)
async def create_analysis_task(
    request: TaskCreate,
    response: Response,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TaskCreateResponse:
    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject identifier in token",
        ) from exc

    user: User | None = await db.get(User, user_id)
    if user is None and payload.email:
        email = payload.email.strip().lower()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_task = Task(
        user_id=user.id,
        product_description=request.product_description,
    )

    # 减少创建延迟：避免多余的 refresh()，并使用 AUTOCOMMIT 降低高并发下的事务竞争
    db.add(new_task)
    try:
        await db.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
    except Exception:
        # 在某些驱动/会话实现下不支持该选项，忽略即可
        pass
    await db.commit()

    created_at = _ensure_utc(getattr(new_task, "created_at", None) or datetime.now(timezone.utc))
    estimated_completion = created_at + timedelta(
        minutes=settings.estimated_processing_minutes
    )
    sse_endpoint = f"{settings.sse_base_path}/{new_task.id}"

    response.headers["Location"] = sse_endpoint

    await _schedule_analysis(new_task.id, settings, user_id=user.id)

    return TaskCreateResponse(
        task_id=new_task.id,
        status=new_task.status,
        created_at=created_at,
        estimated_completion=estimated_completion,
        sse_endpoint=sse_endpoint,
    )


__all__ = ["router"]
