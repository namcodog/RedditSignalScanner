from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession

import fakeredis.aioredis
import pytest

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis_engine import AnalysisResult
from app.services.task_status_cache import TaskStatusCache, TaskStatusPayload
from app.tasks import analysis_task


class _DummySession:
    def __init__(self, task: Any) -> None:
        self._task = task
        self.committed = False

    async def get(self, model: Any, task_id: uuid.UUID) -> Any:
        return self._task

    async def commit(self) -> None:
        self.committed = True


class _DummyTask:
    def __init__(self, status: TaskStatus, error_message: str | None = None) -> None:
        now = datetime.now(timezone.utc)
        self.status = status
        self.error_message = error_message
        self.updated_at = now


@pytest.mark.asyncio
async def test_task_status_cache_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = TaskStatusCache()
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_redis", fake_redis, raising=False)

    payload = TaskStatusPayload(
        task_id=str(uuid.uuid4()),
        status=TaskStatus.PROCESSING.value,
        progress=25,
        message="正在发现相关社区...",
        error=None,
    )

    await cache.set_status(payload, ttl_seconds=5)
    cached = await cache.get_status(payload.task_id)

    assert cached is not None
    assert cached.status == payload.status
    assert cached.progress == payload.progress
    assert cached.message == payload.message


@pytest.mark.asyncio
async def test_task_status_cache_db_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = TaskStatusCache()
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_redis", fake_redis, raising=False)

    task_id = str(uuid.uuid4())
    dummy_task = _DummyTask(TaskStatus.PROCESSING)
    dummy_session = _DummySession(dummy_task)

    cached = await cache.get_status(task_id, session=cast(AsyncSession, dummy_session))

    assert cached is not None
    assert cached.status == TaskStatus.PROCESSING.value
    assert cached.progress == 50
    assert cached.message == "任务正在处理"

    # Cache should now be populated
    cached_again = await cache.get_status(task_id)
    assert cached_again is not None
    assert cached_again.status == cached.status


@pytest.mark.asyncio
async def test_task_status_sync_to_db(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = TaskStatusCache()
    dummy_task = _DummyTask(TaskStatus.PENDING)
    dummy_session = _DummySession(dummy_task)

    payload = TaskStatusPayload(
        task_id=str(uuid.uuid4()),
        status=TaskStatus.COMPLETED.value,
        progress=100,
        message="分析完成",
        error=None,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    await cache.sync_to_db(payload, cast(AsyncSession, dummy_session))

    assert dummy_task.status == TaskStatus.COMPLETED
    assert dummy_session.committed is True


@pytest.mark.asyncio
async def test_task_progress_update(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[TaskStatusPayload] = []

    class _StubCache:
        async def set_status(self, payload: TaskStatusPayload, ttl_seconds: int = 3600) -> None:
            recorded.append(payload)

    stub_cache = _StubCache()
    monkeypatch.setattr(analysis_task, "STATUS_CACHE", stub_cache)

    summary = TaskSummary(
        id=uuid.uuid4(),
        status=TaskStatus.PROCESSING,
        product_description="test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_count=0,
        failure_category=None,
    )

    async def fake_mark_processing(task_id: uuid.UUID, retries: int) -> TaskSummary:
        return summary

    async def fake_store_results(task_id: uuid.UUID, result: AnalysisResult) -> None:
        return None

    async def fake_run_analysis(_: TaskSummary) -> AnalysisResult:
        return AnalysisResult(
            insights={
                "pain_points": [],
                "competitors": [],
                "opportunities": [],
                "action_items": [],
            },
            sources={},
            report_html="<html></html>",
            action_items=[],
            confidence_score=0.0,  # 空结果的置信度为 0
        )

    monkeypatch.setattr(analysis_task, "_mark_processing", fake_mark_processing)
    monkeypatch.setattr(analysis_task, "_store_analysis_results", fake_store_results)
    monkeypatch.setattr(analysis_task, "run_analysis", fake_run_analysis)

    await analysis_task._execute_success_flow(uuid.uuid4(), retries=0)

    progress_steps = [payload.progress for payload in recorded]
    assert progress_steps == [10, 25, 50, 75, 100]
