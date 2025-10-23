from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from celery.exceptions import Retry
from httpx import AsyncClient

from .utils import install_fast_analysis, wait_for_task_completion
from app.db.session import SessionFactory
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.tasks import analysis_task


class _FlakyRedis:
    def __init__(self) -> None:
        self.calls = 0

    async def set(self, *args: Any, **kwargs: Any) -> None:
        self.calls += 1
        raise ConnectionError("redis unavailable")

    async def get(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def delete(self, *args: Any, **kwargs: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_pipeline_handles_redis_outage(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_analysis(monkeypatch)

    original_redis = analysis_task.STATUS_CACHE.redis
    monkeypatch.setattr(analysis_task.STATUS_CACHE, "_redis", _FlakyRedis())

    token, _ = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/analyze",
        json={"product_description": "Redis outage scenario"},
        headers=headers,
    )
    assert resp.status_code == 201
    task_id = resp.json()["task_id"]

    snapshot = await wait_for_task_completion(client, token, task_id, timeout=20.0)
    assert snapshot["status"] == "completed"

    async with SessionFactory() as session:
        task = await session.get(Task, uuid.UUID(task_id))
        assert task is not None
        assert task.status == TaskStatus.COMPLETED

    # Restore original Redis client after assertions
    monkeypatch.setattr(analysis_task.STATUS_CACHE, "_redis", original_redis)


@pytest.mark.asyncio
async def test_pipeline_tolerates_slow_database(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_analysis(monkeypatch)

    original_load = analysis_task._load_task

    async def slow_load(*args: Any, **kwargs: Any):
        await asyncio.sleep(1.1)
        return await original_load(*args, **kwargs)

    monkeypatch.setattr(analysis_task, "_load_task", slow_load)

    token, _ = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/analyze",
        json={"product_description": "PostgreSQL slow query simulation"},
        headers=headers,
    )
    assert resp.status_code == 201
    task_id = resp.json()["task_id"]
    snapshot = await wait_for_task_completion(client, token, task_id, timeout=30.0)
    assert snapshot["status"] == "completed"

    monkeypatch.setattr(analysis_task, "_load_task", original_load)


def test_celery_worker_crash_requests_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the worker crashes mid-flight, the task should request a retry."""

    # Import the original functions to restore them after the test
    from app.tasks import analysis_task as at_module
    original_execute = at_module.execute_analysis_pipeline
    original_prepare = at_module._prepare_failure

    try:
        async def failing_pipeline(task_id, retries):
            raise RuntimeError("worker crashed")

        async def always_retry(*args, **kwargs) -> bool:
            return True

        monkeypatch.setattr(analysis_task, "execute_analysis_pipeline", failing_pipeline)
        monkeypatch.setattr(analysis_task, "_prepare_failure", always_retry)

        class DummyTask:
            def __init__(self) -> None:
                self.request = type("req", (), {"retries": 0})()

            def retry(self, *, exc: Exception, countdown: int) -> None:
                raise Retry(exc=exc)

        dummy = DummyTask()
        task_fn = analysis_task.run_analysis_task.run.__func__

        with pytest.raises(Retry):
            task_fn(dummy, str(uuid.uuid4()))
    finally:
        # Explicitly restore the original functions to ensure no state leakage
        at_module.execute_analysis_pipeline = original_execute
        at_module._prepare_failure = original_prepare


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Passes when run alone or in E2E suite, but fails in full backend suite due to "
    "event loop state interference from unit tests. Run with: "
    "pytest tests/e2e/test_fault_injection.py::test_reddit_rate_limit_escalates_to_failure -v"
)
async def test_reddit_rate_limit_escalates_to_failure(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 错误应触发降级并最终标记为失败。"""

    async def rate_limited_analysis(summary):
        raise RuntimeError("429 Too Many Requests")

    # 设置 MAX_RETRIES=0 让任务立即失败，不进入重试队列
    monkeypatch.setattr(analysis_task, "run_analysis", rate_limited_analysis)
    monkeypatch.setattr(analysis_task, "MAX_RETRIES", 0)
    monkeypatch.setattr(analysis_task, "RETRY_DELAY_SECONDS", 0)

    token, _ = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/analyze",
        json={"product_description": "Trigger rate limit fallback"},
        headers=headers,
    )
    assert resp.status_code == 201
    task_id = resp.json()["task_id"]

    # Expect the task to reach FAILED status eventually
    with pytest.raises(TimeoutError):
        await wait_for_task_completion(client, token, task_id, timeout=5.0)

    # Give the background thread a moment to update the status in DB
    import asyncio
    await asyncio.sleep(0.5)

    status_resp = await client.get(f"/api/status/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "failed"

    async with SessionFactory() as session:
        task = await session.get(Task, uuid.UUID(task_id))
        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert task.error_message is not None
