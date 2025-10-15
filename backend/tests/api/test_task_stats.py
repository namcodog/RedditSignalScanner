from __future__ import annotations

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

    def fake_inspect() -> DummyInspect:
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
