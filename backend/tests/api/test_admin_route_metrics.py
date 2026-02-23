from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


class _StubPipeline:
    def __init__(self, store: dict[str, dict[bytes, bytes]]) -> None:
        self._store = store
        self._keys: list[str] = []

    def hgetall(self, key: str):  # type: ignore[no-untyped-def]
        self._keys.append(key)
        return self

    async def execute(self) -> list[dict[bytes, bytes]]:
        return [self._store.get(key, {}) for key in self._keys]


class _StubRedis:
    def __init__(self, store: dict[str, dict[bytes, bytes]]) -> None:
        self._store = store

    def pipeline(self) -> _StubPipeline:
        return _StubPipeline(self._store)


@pytest.mark.asyncio
async def test_admin_route_metrics_returns_disabled_when_not_enabled(
    client: AsyncClient,
    token_factory,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {token}"}

        setattr(app.state, "route_metrics_redis", None)

        resp = await client.get("/api/admin/metrics/routes", headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["enabled"] is False
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_admin_route_metrics_aggregates_golden_vs_legacy_counts(
    client: AsyncClient,
    token_factory,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {token}"}

        prefix = "metrics:route_calls"
        bucket = int(datetime.now(timezone.utc).timestamp() // 60)
        store = {
            f"{prefix}:{bucket}": {
                b"golden|_total": b"5",
                b"legacy|_total": b"2",
                b"other|_total": b"1",
                b"golden|POST|/api/analyze": b"5",
                b"legacy|GET|/api/admin/metrics/semantic": b"2",
                b"other|GET|/": b"1",
            }
        }
        setattr(app.state, "route_metrics_redis", _StubRedis(store))

        resp = await client.get(
            "/api/admin/metrics/routes",
            headers=headers,
            params={"minutes": 1, "top_n": 5},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["enabled"] is True
        assert payload["window_minutes"] == 1
        assert payload["totals"]["golden"] == 5
        assert payload["totals"]["legacy"] == 2
        assert payload["totals"]["other"] == 1

        top_routes = payload.get("top_routes") or []
        assert isinstance(top_routes, list)
        assert top_routes[0]["group"] == "golden"
        assert top_routes[0]["path"] == "/api/analyze"
        assert top_routes[0]["calls"] == 5
    finally:
        app.dependency_overrides.pop(get_settings, None)

