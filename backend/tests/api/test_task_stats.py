from __future__ import annotations

import time
import pytest
from httpx import AsyncClient


async def test_task_stats_requires_auth(client: AsyncClient) -> None:
    """Stats endpoint should reject unauthenticated requests."""
    response = await client.get("/api/tasks/stats")
    assert response.status_code == 401


async def test_task_stats_returns_expected_counts(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Celery metrics are aggregated into the response payload."""

    class DummyInspect:
        def active(self) -> dict[str, list[int]]:
            return {"worker-a": [1, 2], "worker-b": [3]}

        def reserved(self) -> dict[str, list[int]]:
            return {"worker-a": [4]}

        def scheduled(self) -> dict[str, list[int]]:
            return {"worker-b": [5, 6]}

    def fake_inspect(*_args: object, **_kwargs: object) -> DummyInspect:
        return DummyInspect()

    target = "app.api.routes.tasks.celery_app.control.inspect"
    monkeypatch.setattr(target, fake_inspect)

    response = await client.get(
        "/api/tasks/stats",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_workers"] == 2
    assert payload["active_tasks"] == 3
    assert payload["reserved_tasks"] == 1
    assert payload["scheduled_tasks"] == 2
    assert payload["total_tasks"] == 6


async def test_task_stats_falls_back_to_ping_when_inspect_returns_empty(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Celery inspect times out, /tasks/stats should still report worker presence via ping."""

    class DummyInspect:
        def active(self) -> dict[str, list[int]]:
            return {}

        def reserved(self) -> dict[str, list[int]]:
            return {}

        def scheduled(self) -> dict[str, list[int]]:
            return {}

    def fake_inspect(*_args: object, **_kwargs: object) -> DummyInspect:
        return DummyInspect()

    def fake_ping(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        # Celery control.ping() commonly returns a list of {worker_name: {"ok": "pong"}} payloads.
        return [
            {"worker-a": {"ok": "pong"}},
            {"worker-b": {"ok": "pong"}},
        ]

    monkeypatch.setattr("app.api.routes.tasks.celery_app.control.inspect", fake_inspect)
    monkeypatch.setattr("app.api.routes.tasks.celery_app.control.ping", fake_ping)

    response = await client.get(
        "/api/tasks/stats",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_workers"] == 2
    assert payload["active_tasks"] == 0
    assert payload["reserved_tasks"] == 0
    assert payload["scheduled_tasks"] == 0
    assert payload["total_tasks"] == 0


async def test_task_stats_returns_fast_when_broker_unavailable(
    client: AsyncClient,
    auth_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    大白话：broker 掉线时，/tasks/stats 不能卡住（否则监控页也跟着挂）。
    """

    def slow_inspect(*_args: object, **_kwargs: object):
        time.sleep(5)
        return None

    monkeypatch.setattr("app.api.routes.tasks.celery_app.control.inspect", slow_inspect)

    started = time.perf_counter()
    response = await client.get(
        "/api/tasks/stats",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_workers"] == 0
    assert elapsed < 3.0
