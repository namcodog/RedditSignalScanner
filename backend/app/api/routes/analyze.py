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


async def _schedule_analysis(task_id: uuid.UUID, settings: Settings) -> None:
    """
    Dispatch the analysis job to Celery; fallback to inline execution in dev/test.
    """

    inline_preferred = settings.environment.lower() in {
        "development",
        "test",
    } and os.getenv("ENABLE_CELERY_DISPATCH", "0").lower() not in {"1", "true", "yes"}

    if inline_preferred:
        logger.info(
            "Environment %s running analysis task %s inline (Celery bypass for local/dev).",
            settings.environment,
            task_id,
        )
        # 将耗时的分析流程放到独立线程+专用事件循环中执行，避免与 FastAPI 事件循环竞争导致状态滞后
        # 这样可以确保在高并发测试场景下，失败/完成状态能在几秒内稳定落库
        loop = asyncio.get_running_loop()

        def _runner_sync() -> None:
            from app.tasks.analysis_task import (
                FinalRetryExhausted,
                TaskNotFoundError,
                execute_analysis_pipeline as _exec,
                _run_async as _run,
            )

            try:
                _run(_exec(task_id))
            except FinalRetryExhausted as exc:
                logger.error(
                    "Inline analysis task %s failed after retries: %s", task_id, exc
                )
            except TaskNotFoundError:
                logger.warning(
                    "Inline analysis task %s aborted: task not found.", task_id
                )
            except Exception:
                logger.exception(
                    "Inline analysis task %s encountered an unexpected error.", task_id
                )

        loop.run_in_executor(None, _runner_sync)
        return

    try:
        sent = celery_app.send_task("tasks.analysis.run", args=[str(task_id)])
        logger.info("Dispatched analysis task %s to Celery (id=%s).", task_id, sent.id)
    except Exception as exc:  # pragma: no cover - depends on runtime availability
        if settings.environment.lower() in {"development", "test"}:
            logger.warning(
                "Celery dispatch failed for task %s; falling back to inline execution. Error: %s",
                task_id,
                exc,
            )
            loop = asyncio.get_running_loop()
            loop.create_task(execute_analysis_pipeline(task_id))
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

    await _schedule_analysis(new_task.id, settings)

    return TaskCreateResponse(
        task_id=new_task.id,
        status=new_task.status,
        created_at=created_at,
        estimated_completion=estimated_completion,
        sse_endpoint=sse_endpoint,
    )


__all__ = ["router"]
