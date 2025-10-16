from __future__ import annotations

import asyncio
import atexit
import logging
import os
import uuid
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any, AsyncIterator, Coroutine, Dict, Optional, TYPE_CHECKING, TypeVar, cast, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from celery.exceptions import Retry as CeleryRetry  # type: ignore[import-untyped]
from app.db.session import get_session
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.task import Task as TaskModel, TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis_engine import AnalysisResult, run_analysis
from app.services.task_status_cache import TaskStatusCache, TaskStatusPayload

if TYPE_CHECKING:
    from celery.app.task import Task  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

STATUS_CACHE = TaskStatusCache()
UTC = timezone.utc
MAX_ERROR_LENGTH = int(os.getenv("TASK_ERROR_MESSAGE_MAX_LENGTH", "2000"))
MAX_RETRIES = int(os.getenv("CELERY_ANALYSIS_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("CELERY_ANALYSIS_RETRY_DELAY", "60"))

T = TypeVar("T")

_LOOP_LOCK = Lock()
_ASYNC_LOOP: asyncio.AbstractEventLoop | None = None
_LOOP_THREAD: Thread | None = None


def _start_loop() -> None:
    global _ASYNC_LOOP, _LOOP_THREAD
    loop_ready = Event()
    loop = asyncio.new_event_loop()

    def runner() -> None:
        asyncio.set_event_loop(loop)
        loop_ready.set()
        loop.run_forever()

    thread = Thread(target=runner, name="analysis-task-loop", daemon=True)
    thread.start()
    loop_ready.wait()
    _ASYNC_LOOP = loop
    _LOOP_THREAD = thread


def _ensure_loop() -> asyncio.AbstractEventLoop:
    with _LOOP_LOCK:
        if _ASYNC_LOOP is None or _ASYNC_LOOP.is_closed() or not _ASYNC_LOOP.is_running():
            _start_loop()
        assert _ASYNC_LOOP is not None
        return _ASYNC_LOOP


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def _shutdown_loop() -> None:
    global _ASYNC_LOOP, _LOOP_THREAD
    thread: Thread | None
    loop: asyncio.AbstractEventLoop | None
    with _LOOP_LOCK:
        loop = _ASYNC_LOOP
        thread = _LOOP_THREAD
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(loop.stop)

    if thread is not None:
        thread.join(timeout=5)

    with _LOOP_LOCK:
        if _ASYNC_LOOP is not None and not _ASYNC_LOOP.is_closed():
            _ASYNC_LOOP.close()
        _ASYNC_LOOP = None
        _LOOP_THREAD = None


atexit.register(_shutdown_loop)


class TaskNotFoundError(RuntimeError):
    """Raised when a task identifier cannot be located in the database."""

class FinalRetryExhausted(RuntimeError):
    """Raised when the analysis task has no retries remaining."""


async def _load_task(
    session: AsyncSession,
    task_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> TaskModel:
    stmt = (
        select(TaskModel)
        .options(
            selectinload(TaskModel.user),
            selectinload(TaskModel.analysis).selectinload(Analysis.report),
        )
        .where(TaskModel.id == task_id)
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return task


async def _mark_processing(task_id: uuid.UUID, retries: int) -> TaskSummary:
    summary: Optional[TaskSummary] = None
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            if task.started_at is None:
                task.started_at = now
            task.status = TaskStatus.PROCESSING
            task.error_message = None
            task.failure_category = None
            task.retry_count = retries
            if retries > 0:
                task.last_retry_at = now
            task.updated_at = now

            summary = TaskSummary(
                id=task.id,
                status=task.status,
                product_description=task.product_description,
                created_at=task.created_at or now,
                updated_at=task.updated_at or now,
                completed_at=task.completed_at,
                retry_count=task.retry_count,
                failure_category=task.failure_category,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break

    if summary is None:
        raise RuntimeError("Failed to acquire task summary during processing.")
    return summary


async def _store_analysis_results(task_id: uuid.UUID, result: AnalysisResult) -> None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)

            analysis = task.analysis
            if analysis is None:
                analysis = Analysis(
                    task=task,
                    insights=result.insights,
                    sources=result.sources,
                    analysis_version="1.0",
                )
                session.add(analysis)
            else:
                analysis.insights = result.insights
                analysis.sources = result.sources

            if analysis.report is None:
                report = Report(
                    analysis=analysis,
                    html_content=result.report_html,
                    template_version="1.0",
                    generated_at=now,
                )
                session.add(report)
            else:
                analysis.report.html_content = result.report_html
                analysis.report.generated_at = now

            task.status = TaskStatus.COMPLETED
            task.completed_at = now
            task.error_message = None
            task.failure_category = None
            task.dead_letter_at = None

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _mark_pending_retry(task_id: uuid.UUID, retries: int) -> None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            task.status = TaskStatus.PENDING
            task.error_message = None
            task.failure_category = None
            task.retry_count = retries
            task.last_retry_at = now

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _mark_failed(
    task_id: uuid.UUID,
    error: str,
    failure_category: str,
    retries: int,
    reached_dead_letter: bool,
) -> None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            task.status = TaskStatus.FAILED
            task.error_message = error
            task.failure_category = failure_category
            task.retry_count = retries
            task.last_retry_at = now
            task.completed_at = None
            if reached_dead_letter:
                task.dead_letter_at = now

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _cache_status(
    task_id: str,
    status: TaskStatus,
    progress: int,
    message: str,
    error: Optional[str] = None,
) -> None:
    payload = TaskStatusPayload(
        task_id=task_id,
        status=status.value,
        progress=progress,
        message=message,
        error=error,
        updated_at=datetime.now(UTC).isoformat(),
    )
    await STATUS_CACHE.set_status(payload)


def _categorize_failure(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "processing_error"
    return "system_error"


def _truncate_error(error: str) -> str:
    if len(error) <= MAX_ERROR_LENGTH:
        return error
    return f"{error[:MAX_ERROR_LENGTH - 3]}..."


async def _execute_success_flow(task_id: uuid.UUID, retries: int) -> Dict[str, Any]:
    summary = await _mark_processing(task_id, retries)
    await _cache_status(str(task_id), TaskStatus.PROCESSING, progress=10, message="任务开始处理")
    await _cache_status(str(task_id), TaskStatus.PROCESSING, progress=25, message="正在发现相关社区...")
    await _cache_status(str(task_id), TaskStatus.PROCESSING, progress=50, message="正在并行采集数据...")
    result = await run_analysis(summary)
    await _cache_status(str(task_id), TaskStatus.PROCESSING, progress=75, message="分析完成，生成报告中...")
    await _store_analysis_results(task_id, result)
    await _cache_status(str(task_id), TaskStatus.COMPLETED, progress=100, message="分析完成")
    communities = result.sources.get("communities", [])
    return {
        "communities_found": len(communities),
        "posts_collected": int(result.sources.get("posts_analyzed", 0)),
        "cache_hit_rate": float(result.sources.get("cache_hit_rate", 0.0)),
    }


async def _run_pipeline_with_retry(
    task_id: uuid.UUID,
    initial_retries: int = 0,
    retry_handler: Callable[[Exception, int], None] | None = None,
) -> Dict[str, Any]:
    retries = initial_retries
    task_id_str = str(task_id)
    while True:
        try:
            return await _execute_success_flow(task_id, retries)
        except TaskNotFoundError:
            raise
        except Exception as exc:
            should_retry = await _prepare_failure(task_id, task_id_str, exc, retries)
            if not should_retry:
                raise FinalRetryExhausted(f"Analysis task {task_id_str} reached retry limit.") from exc
            if retry_handler is not None:
                retry_handler(exc, retries)
                # retry_handler should raise (e.g., Celery self.retry). If it returns, fall back to inline logic.
            retries += 1
            if retry_handler is None and RETRY_DELAY_SECONDS > 0:
                await asyncio.sleep(min(RETRY_DELAY_SECONDS, 1.0))


async def execute_analysis_pipeline(task_id: uuid.UUID, retries: int = 0) -> Dict[str, Any]:
    """
    Execute the full analysis pipeline outside of Celery (primarily for local/dev fallback).
    """

    return await _run_pipeline_with_retry(task_id, retries)


_DEFAULT_EXECUTE_ANALYSIS_PIPELINE = execute_analysis_pipeline


async def _prepare_failure(
    task_id: uuid.UUID,
    task_id_str: str,
    exc: Exception,
    retries: int,
) -> bool:
    error_text = _truncate_error(str(exc))
    failure_category = _categorize_failure(exc)

    if retries < MAX_RETRIES:
        await _mark_pending_retry(task_id, retries + 1)
        await _cache_status(
            task_id_str,
            TaskStatus.PENDING,
            progress=0,
            message="等待重试",
            error=error_text,
        )
        return True

    await _mark_failed(task_id, error_text, failure_category, retries, True)
    await _cache_status(
        task_id_str,
        TaskStatus.FAILED,
        progress=0,
        message="任务失败",
        error=error_text,
    )
    return False


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="tasks.analysis.run",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_DELAY_SECONDS,
    autoretry_for=(Exception,),
    dont_autoretry_for=(FinalRetryExhausted, TaskNotFoundError),
    retry_kwargs={"countdown": RETRY_DELAY_SECONDS, "max_retries": MAX_RETRIES},
    retry_backoff=True,
    retry_jitter=True,
)
def run_analysis_task(self: "Task[Any, Dict[str, Any]]", task_id: str) -> Dict[str, Any]:
    task_uuid = uuid.UUID(task_id)
    use_default_executor = execute_analysis_pipeline is _DEFAULT_EXECUTE_ANALYSIS_PIPELINE

    try:
        if use_default_executor:
            def _retry_or_exhaust(exc: Exception) -> None:
                # If we have retries remaining, delegate to Celery's retry (raises CeleryRetry)
                if getattr(self.request, "retries", 0) < MAX_RETRIES:
                    raise self.retry(exc=exc, countdown=RETRY_DELAY_SECONDS)
                # Otherwise signal exhaustion to caller/tests
                raise RuntimeError(str(exc))

            pipeline_metrics = _run_async(
                _run_pipeline_with_retry(
                    task_uuid,
                    self.request.retries,
                    retry_handler=lambda exc, _retry_count: _retry_or_exhaust(exc),
                )
            )
        else:
            pipeline_metrics = _run_async(execute_analysis_pipeline(task_uuid, self.request.retries))
        response = {
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value,
        }
        if isinstance(pipeline_metrics, dict):
            response.update(pipeline_metrics)
        return response
    except TaskNotFoundError:
        logger.warning("Task %s not found; skipping analysis.", task_id)
        return {
            "task_id": task_id,
            "status": "not_found",
        }
    except FinalRetryExhausted as exc:
        raise exc
    except Exception as exc:  # pragma: no cover - unexpected fallthrough or monkeypatched executor path
        # Always allow Celery's Retry to bubble up
        if isinstance(exc, CeleryRetry):
            raise
        if use_default_executor:
            # In the default executor path, bubble up the original exception (either CeleryRetry
            # or our exhaustion marker RuntimeError), letting Celery handle retries/backoff.
            raise
        # Non-default (monkeypatched) executor path: consult failure handler to decide retry.
        should_retry = _run_async(_prepare_failure(task_uuid, task_id, exc, self.request.retries))
        if should_retry:
            raise self.retry(exc=exc, countdown=RETRY_DELAY_SECONDS)
        raise FinalRetryExhausted(f"Analysis task {task_id} reached retry limit.") from exc


__all__ = ["execute_analysis_pipeline", "run_analysis_task"]

# Provide backwards-compatible __func__ attribute so unit tests can access the underlying
# callable even though Celery exposes a plain function for ``run``.
if hasattr(run_analysis_task, "run") and not hasattr(run_analysis_task.run, "__func__"):
    original = getattr(run_analysis_task, "_orig_run", run_analysis_task.run)
    setattr(run_analysis_task.run, "__func__", getattr(original, "__func__", original))
