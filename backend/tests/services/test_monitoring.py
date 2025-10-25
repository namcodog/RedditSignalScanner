from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict

import pytest

from app.services.monitoring import MonitoringService


class _FakeInspect:
    def __init__(
        self,
        *,
        active: Dict[str, list[Any]] | None = None,
        reserved: Dict[str, list[Any]] | None = None,
        scheduled: Dict[str, list[Any]] | None = None,
        stats: Dict[str, Dict[str, Any]] | None = None,
    ) -> None:
        self._active = active or {}
        self._reserved = reserved or {}
        self._scheduled = scheduled or {}
        self._stats = stats or {}

    def active(self) -> Dict[str, list[Any]]:
        return self._active

    def reserved(self) -> Dict[str, list[Any]]:
        return self._reserved

    def scheduled(self) -> Dict[str, list[Any]]:
        return self._scheduled

    def stats(self) -> Dict[str, Dict[str, Any]]:
        return self._stats


class _FakeControl:
    def __init__(self, inspect: _FakeInspect | None) -> None:
        self._inspect = inspect

    def inspect(self) -> _FakeInspect | None:
        return self._inspect


class _FakeCelery:
    def __init__(self, inspect: _FakeInspect | None) -> None:
        self.control = _FakeControl(inspect)


class _FakeRedis:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = dict(payload)

    async def info(self) -> Dict[str, Any]:
        return dict(self._payload)


class _AsyncFakeRedis(_FakeRedis):
    async def info(self) -> Dict[str, Any]:
        return await super().info()


def test_celery_stats_with_running_workers() -> None:
    inspect = _FakeInspect(
        active={"worker-1": [1, 2], "worker-2": [3]},
        reserved={"worker-1": [4]},
        scheduled={"worker-2": [5, 6]},
        stats={
            "worker-1": {"total": {"tasks.analysis.run": 7}},
            "worker-2": {"total": {"tasks.analysis.run": 3}, "failed": 1},
        },
    )
    celery = _FakeCelery(inspect)
    redis_client = _FakeRedis({})

    service = MonitoringService(redis_client, celery)  # type: ignore[arg-type]

    stats = service.get_celery_stats()
    assert stats["active_workers"] == 2
    assert stats["active_tasks"] == 3
    assert stats["reserved_tasks"] == 1
    assert stats["scheduled_tasks"] == 2
    assert stats["queued_tasks"] == 3
    assert stats["completed_tasks"] == 10
    assert stats["failed_tasks"] == 1


def test_celery_stats_when_inspect_unavailable() -> None:
    celery = _FakeCelery(None)
    redis_client = _FakeRedis({})

    service = MonitoringService(redis_client, celery)  # type: ignore[arg-type]

    stats = service.get_celery_stats()
    assert stats == {
        "active_workers": 0,
        "active_tasks": 0,
        "reserved_tasks": 0,
        "scheduled_tasks": 0,
        "queued_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
    }


@pytest.mark.asyncio
async def test_redis_stats_compute_hit_rate() -> None:
    redis_payload = {
        "connected_clients": 5,
        "used_memory": 8 * 1024 * 1024,  # 8MB
        "keyspace_hits": 80,
        "keyspace_misses": 20,
        "uptime_in_seconds": 3600,
        "instantaneous_ops_per_sec": 140,
    }
    redis_client = _FakeRedis(redis_payload)
    celery = _FakeCelery(None)

    service = MonitoringService(redis_client, celery)  # type: ignore[arg-type]

    stats = await service.get_redis_stats()
    assert stats["connected_clients"] == 5
    assert stats["used_memory_mb"] == 8.0
    assert stats["hit_rate"] == pytest.approx(0.8, rel=1e-4)
    assert stats["uptime_seconds"] == 3600
    assert stats["ops_per_sec"] == 140


@pytest.mark.asyncio
async def test_async_redis_client_supported() -> None:
    redis_payload = {
        "connected_clients": 2,
        "used_memory": 4 * 1024 * 1024,
        "keyspace_hits": 20,
        "keyspace_misses": 5,
        "uptime_in_seconds": 120,
        "instantaneous_ops_per_sec": 42,
    }
    redis_client = _AsyncFakeRedis(redis_payload)
    celery = _FakeCelery(None)

    service = MonitoringService(redis_client, celery)  # type: ignore[arg-type]

    stats = await service.get_redis_stats()
    assert stats["connected_clients"] == 2
    assert stats["hit_rate"] == pytest.approx(0.8, rel=1e-4)
