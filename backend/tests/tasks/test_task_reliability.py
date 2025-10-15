from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from celery.exceptions import Retry

from app.tasks import analysis_task
from scripts.check_celery_health import CeleryHealthError, check_celery_health


def test_run_analysis_task_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Celery task should request retries for transient failures and eventually succeed."""
    attempts: list[int] = []

    async def fake_execute(task_id: uuid.UUID, retries: int) -> None:
        attempts.append(retries)
        if len(attempts) < 3:
            raise RuntimeError("temporary failure")

    async def fake_prepare(task_id: uuid.UUID, task_id_str: str, exc: Exception, retries: int) -> bool:
        return True

    def fake_run_async(coro):
        result = asyncio.run(coro)
        return result

    class DummyCache:
        async def set_status(self, payload) -> None:  # pragma: no cover - noop
            return None

    class DummyTask:
        def __init__(self) -> None:
            self.request = SimpleNamespace(retries=0)
            self.retry_countdowns: list[int] = []

        def retry(self, *, exc: Exception, countdown: int) -> None:
            self.retry_countdowns.append(countdown)
            raise Retry(exc=exc)

    monkeypatch.setattr(analysis_task, "_execute_success_flow", fake_execute)
    monkeypatch.setattr(analysis_task, "_prepare_failure", fake_prepare)
    monkeypatch.setattr(analysis_task, "_run_async", fake_run_async)
    monkeypatch.setattr(analysis_task, "STATUS_CACHE", DummyCache())

    dummy_task = DummyTask()
    task_id = str(uuid.uuid4())

    task_fn = analysis_task.run_analysis_task.run.__func__

    with pytest.raises(Retry):
        task_fn(dummy_task, task_id)
    dummy_task.request.retries += 1

    with pytest.raises(Retry):
        task_fn(dummy_task, task_id)
    dummy_task.request.retries += 1

    result = task_fn(dummy_task, task_id)

    assert result["status"] == "completed"
    assert attempts == [0, 1, 2]
    assert len(dummy_task.retry_countdowns) == 2


def test_run_analysis_task_respects_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Celery task should stop retrying once the configured threshold is reached."""
    attempts: list[int] = []

    async def fake_execute(task_id: uuid.UUID, retries: int) -> None:
        attempts.append(retries)
        raise RuntimeError("permanent failure")

    async def fake_prepare(task_id: uuid.UUID, task_id_str: str, exc: Exception, retries: int) -> bool:
        return retries < 2

    def fake_run_async(coro):
        return asyncio.run(coro)

    class DummyCache:
        async def set_status(self, payload) -> None:
            return None

    class DummyTask:
        def __init__(self) -> None:
            self.request = SimpleNamespace(retries=0)

        def retry(self, *, exc: Exception, countdown: int) -> None:
            raise Retry(exc=exc)

    monkeypatch.setattr(analysis_task, "_execute_success_flow", fake_execute)
    monkeypatch.setattr(analysis_task, "_prepare_failure", fake_prepare)
    monkeypatch.setattr(analysis_task, "_run_async", fake_run_async)
    monkeypatch.setattr(analysis_task, "STATUS_CACHE", DummyCache())
    monkeypatch.setattr(analysis_task, "MAX_RETRIES", 2)

    dummy_task = DummyTask()
    task_id = str(uuid.uuid4())

    task_fn = analysis_task.run_analysis_task.run.__func__

    with pytest.raises(Retry):
        task_fn(dummy_task, task_id)
    dummy_task.request.retries += 1

    with pytest.raises(Retry):
        task_fn(dummy_task, task_id)
    dummy_task.request.retries += 1

    with pytest.raises(RuntimeError):
        task_fn(dummy_task, task_id)

    assert attempts == [0, 1, 2]


@pytest.mark.asyncio
async def test_check_celery_health_reports_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health script aggregates worker metrics and tolerates transient Redis outages."""

    class DummyInspect:
        def active(self) -> dict[str, list[int]]:
            return {"worker-1": [1, 2]}

        def reserved(self) -> dict[str, list[int]]:
            return {"worker-1": [3]}

        def scheduled(self) -> dict[str, list[int]]:
            return {}

        def stats(self) -> dict[str, dict[str, dict[str, int]]]:
            return {"worker-1": {"total": {"tasks.analysis.run": 10}, "failures": {"tasks.analysis.run": 0}}}

    class DummyRedis:
        def __init__(self) -> None:
            self.calls = 0

        async def ping(self) -> bool:
            self.calls += 1
            if self.calls < 3:
                raise ConnectionError("unavailable")
            return True

        async def close(self) -> None:
            return None

    class DummyCache:
        def __init__(self) -> None:
            self.redis = DummyRedis()

    monkeypatch.setattr("scripts.check_celery_health.celery_app.control.inspect", lambda: DummyInspect())
    monkeypatch.setattr("scripts.check_celery_health.TaskStatusCache", DummyCache)

    summary = await check_celery_health()

    assert summary["active_workers"] == 1
    assert summary["reserved_tasks"] == 1
    assert summary["total_tasks"] == 3


@pytest.mark.asyncio
async def test_check_celery_health_detects_failure_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health script raises when failure rate exceeds the configured threshold."""

    class UnhealthyInspect:
        def active(self) -> dict[str, list[int]]:
            return {"worker-1": [1]}

        def reserved(self) -> dict[str, list[int]]:
            return {}

        def scheduled(self) -> dict[str, list[int]]:
            return {}

        def stats(self) -> dict[str, dict[str, dict[str, int]]]:
            return {"worker-1": {"total": {"tasks.analysis.run": 10}, "failures": {"tasks.analysis.run": 2}}}

    class HealthyCache:
        def __init__(self) -> None:
            class _Redis:
                async def ping(self) -> bool:
                    return True

                async def close(self) -> None:
                    return None

            self.redis = _Redis()

    monkeypatch.setattr("scripts.check_celery_health.celery_app.control.inspect", lambda: UnhealthyInspect())
    monkeypatch.setattr("scripts.check_celery_health.TaskStatusCache", HealthyCache)

    with pytest.raises(CeleryHealthError):
        await check_celery_health(max_failure_rate=0.1)
