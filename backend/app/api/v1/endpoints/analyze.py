from __future__ import annotations

import asyncio
import logging
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.core.tenant_context import set_current_user_id, unset_current_user_id
from app.db.session import get_session
from app.db.session import SessionFactory
from app.models.analysis import Analysis
from app.models.example_library import ExampleLibrary
from app.models.report import Report
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskCreateResponse
from app.tasks.analysis_task import execute_analysis_pipeline
from app.services.analysis.topic_profiles import TopicProfile, load_topic_profiles, match_topic_profile
from app.services.infrastructure.task_status_cache import TaskStatusCache, TaskStatusPayload

router = APIRouter()
logger = logging.getLogger(__name__)
STATUS_CACHE = TaskStatusCache()


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_int_env(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 0)


def _example_delay_seconds() -> int:
    min_delay = _parse_int_env("EXAMPLE_REPORT_DELAY_MIN_SECONDS", 10)
    max_delay = _parse_int_env("EXAMPLE_REPORT_DELAY_MAX_SECONDS", 20)
    if max_delay < min_delay:
        max_delay = min_delay
    return random.randint(min_delay, max_delay)


async def _schedule_example_report(
    *,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    example_id: uuid.UUID,
    delay_seconds: int,
) -> None:
    async def _set_cache(
        *,
        status_value: str,
        progress: int,
        message: str,
        stage: str | None = None,
        error: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        try:
            await asyncio.wait_for(
                STATUS_CACHE.set_status(
                    TaskStatusPayload(
                        task_id=str(task_id),
                        status=status_value,
                        progress=progress,
                        message=message,
                        stage=stage,
                        error=error,
                        details=details,
                    )
                ),
                timeout=0.3,
            )
        except Exception:
            return

    async def _mark_failed(reason: str) -> None:
        async with SessionFactory() as session:
            set_current_user_id(user_id)
            try:
                task = await session.get(Task, task_id)
                if task is None:
                    return
                task.status = TaskStatus.FAILED
                task.error_message = reason
                task.failure_category = "processing_error"
                task.completed_at = datetime.now(timezone.utc)
                await session.commit()
            finally:
                unset_current_user_id()
        await _set_cache(
            status_value="failed",
            progress=0,
            message="示例报告生成失败",
            stage="failed",
            error=reason[:300],
        )

    async def _run_example_flow() -> None:
        await _set_cache(
            status_value="pending",
            progress=0,
            message="任务排队中",
            stage="dispatch",
            details={"dispatch_mode": "example"},
        )

        async with SessionFactory() as session:
            set_current_user_id(user_id)
            try:
                task = await session.get(Task, task_id)
                if task is None:
                    return
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now(timezone.utc)
                await session.commit()
            finally:
                unset_current_user_id()

        await _set_cache(
            status_value="processing",
            progress=25,
            message="分析处理中",
            stage="processing",
        )

        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        async with SessionFactory() as session:
            set_current_user_id(user_id)
            try:
                example = await session.get(ExampleLibrary, example_id)
                task = await session.get(Task, task_id)
                if task is None or example is None or not example.is_active:
                    raise RuntimeError("Example not available")

                analysis = Analysis(
                    task_id=task_id,
                    insights=example.analysis_insights,
                    sources=example.analysis_sources,
                    action_items=example.analysis_action_items,
                    confidence_score=example.analysis_confidence_score,
                    analysis_version=example.analysis_version,
                )
                session.add(analysis)
                await session.flush()

                report = Report(
                    analysis_id=analysis.id,
                    html_content=example.report_html,
                    template_version=example.report_template_version,
                )
                session.add(report)

                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)
                await session.commit()
            finally:
                unset_current_user_id()

        await _set_cache(
            status_value="completed",
            progress=100,
            message="分析完成",
            stage="completed",
        )

    try:
        if delay_seconds <= 0:
            await _run_example_flow()
        else:
            asyncio.create_task(_run_example_flow())
    except Exception as exc:
        await _mark_failed(str(exc))


async def _schedule_analysis(task_id: uuid.UUID, user_id: uuid.UUID, settings: Settings) -> None:
    """
    Dispatch the analysis job to Celery.

    大白话：
    - 如果你没开 Celery（ENABLE_CELERY_DISPATCH=0），那就本地 inline 跑（开发/测试更省事）。
    - 如果你开了 Celery（ENABLE_CELERY_DISPATCH=1），那就必须真的投递到队列；投不进去就明确报错，不能假装成功。
    """

    async def _mark_dispatch(
        *,
        mode: str,
        celery_id: str | None = None,
        error: str | None = None,
    ) -> None:
        details: dict[str, str] = {"dispatch_mode": mode}
        if celery_id:
            details["celery_task_id"] = celery_id
        if error:
            details["celery_error"] = error[:300]
        try:
            await asyncio.wait_for(
                STATUS_CACHE.set_status(
                    TaskStatusPayload(
                        task_id=str(task_id),
                        status="pending",
                        progress=0,
                        message="任务排队中",
                        stage="dispatch",
                        details=details,
                    )
                ),
                timeout=0.3,
            )
        except Exception:
            # Redis 不可用/超时时，别让创建任务变慢或失败
            return

    inline_preferred = settings.environment.lower() in {
        "development",
        "test",
    } and os.getenv("ENABLE_CELERY_DISPATCH", "1").lower() not in {"1", "true", "yes"}

    if inline_preferred:
        # 在测试环境直接在当前事件循环内执行，避免跨事件循环的 Future 绑定报错
        if settings.environment.lower() == "test":
            await _mark_dispatch(mode="inline_test")
            logger.info(
                "Environment %s executing analysis task %s inline on request loop (test-safe).",
                settings.environment,
                task_id,
            )
            try:
                await execute_analysis_pipeline(task_id, user_id=user_id)
            except Exception as exc:  # pragma: no cover - surfaced到调用方
                logger.exception("Inline analysis task %s failed: %s", task_id, exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Analysis failed",
                ) from exc
            return

        # 开发环境：不要用 executor + 另一个事件循环（会触发 asyncpg/SQLAlchemy 跨 loop Future 报错）
        await _mark_dispatch(mode="inline_dev")
        logger.info(
            "Environment %s scheduling analysis task %s inline (Celery bypass for local/dev).",
            settings.environment,
            task_id,
        )
        asyncio.create_task(execute_analysis_pipeline(task_id, user_id=user_id))
        return

    try:
        dispatch_timeout = float(os.getenv("CELERY_DISPATCH_TIMEOUT_SECONDS", "2.0"))
        sent = await asyncio.wait_for(
            asyncio.to_thread(
                celery_app.send_task,
                "tasks.analysis.run",
                args=[str(task_id), str(user_id)],
            ),
            timeout=dispatch_timeout,
        )
        await _mark_dispatch(mode="celery", celery_id=sent.id)
        logger.info("Dispatched analysis task %s to Celery (id=%s).", task_id, sent.id)
    except Exception as exc:  # pragma: no cover - depends on runtime availability
        await _mark_dispatch(mode="celery_dispatch_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis queue unavailable, please retry later.",
        ) from exc


def _resolve_topic_profile(topic_profile_id: str | None) -> TopicProfile | None:
    if topic_profile_id is None:
        return None
    profiles = load_topic_profiles()
    match = match_topic_profile(topic_profile_id, profiles)
    if match is None or not match.id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown topic_profile_id (check config/topic_profiles.yaml)",
        )
    return match


def _resolve_mode(request_mode: str | None, profile: TopicProfile | None) -> str:
    if request_mode:
        return request_mode
    if profile is not None and getattr(profile, "mode", ""):
        return profile.mode
    return "market_insight"


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

    topic_profile = _resolve_topic_profile(request.topic_profile_id)
    topic_profile_id = topic_profile.id.strip().lower() if topic_profile else None
    # audit_level 是“产品意图”：允许显式覆盖；否则按默认规则填
    audit_level = request.audit_level or ("gold" if topic_profile_id else "lab")
    mode = _resolve_mode(request.mode, topic_profile)

    example: ExampleLibrary | None = None
    product_description = request.product_description
    if request.example_id is not None:
        example = await db.get(ExampleLibrary, request.example_id)
        if example is None or not example.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Example not available",
            )
        sources = example.analysis_sources or {}
        if "report_structured" not in sources:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Example report_structured missing",
            )
        product_description = example.prompt

    new_task = Task(
        user_id=user.id,
        product_description=product_description,
        mode=mode,
        audit_level=audit_level,
        topic_profile_id=topic_profile_id,
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
    if example is None:
        estimated_completion = created_at + timedelta(
            minutes=settings.estimated_processing_minutes
        )
        delay_seconds = None
    else:
        delay_seconds = _example_delay_seconds()
        estimated_completion = created_at + timedelta(seconds=delay_seconds)
    sse_endpoint = f"{settings.sse_base_path}/{new_task.id}"

    response.headers["Location"] = sse_endpoint
    try:
        if example is None:
            await _schedule_analysis(new_task.id, user_id, settings)
        else:
            await _schedule_example_report(
                task_id=new_task.id,
                user_id=user_id,
                example_id=example.id,
                delay_seconds=delay_seconds or 0,
            )
    except HTTPException as exc:
        # 如果队列不可用：不要留下“孤儿 task”（用户重试会越积越多，且永远不会完成）
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            try:
                await db.delete(new_task)
                await db.commit()
            except Exception:
                await db.rollback()
            raise
        raise

    return TaskCreateResponse(
        task_id=new_task.id,
        status=new_task.status,
        created_at=created_at,
        estimated_completion=estimated_completion,
        sse_endpoint=sse_endpoint,
    )
