from __future__ import annotations

from typing import Optional

import fakeredis.aioredis as fakeredis
from fakeredis import FakeServer
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.route_metrics import (
    DEFAULT_ROUTE_METRICS_KEY_PREFIX,
    ENABLE_ROUTE_METRICS_ENV,
    RouteMetricsMiddleware,
)

pytestmark = pytest.mark.asyncio


async def _find_counter_value(
    client: fakeredis.FakeRedis,
    *,
    group: str,
    method: str,
    path: str,
) -> Optional[int]:
    pattern = f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:*"
    keys = await client.keys(pattern)
    if not keys:
        return None

    field = f"{group}|{method.upper()}|{path}"
    for key in keys:
        raw = await client.hget(key, field)
        if raw is None:
            continue
        decoded = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        return int(decoded)
    return None


async def _find_status_counter_value(
    client: fakeredis.FakeRedis,
    *,
    group: str,
    status_code: int,
) -> Optional[int]:
    pattern = f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:*"
    keys = await client.keys(pattern)
    if not keys:
        return None

    field = f"{group}|status|{int(status_code)}"
    for key in keys:
        raw = await client.hget(key, field)
        if raw is None:
            continue
        decoded = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        return int(decoded)
    return None


async def test_route_metrics_counts_golden_and_legacy(monkeypatch) -> None:
    monkeypatch.setenv(ENABLE_ROUTE_METRICS_ENV, "1")

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    app = FastAPI()
    app.add_middleware(RouteMetricsMiddleware)
    app.state.route_metrics_redis = redis_client

    @app.get("/api/test/golden")
    async def golden() -> dict[str, bool]:
        return {"ok": True}

    golden.__module__ = "app.api.v1.endpoints.test"

    @app.get("/api/test/legacy")
    async def legacy() -> dict[str, bool]:
        return {"ok": True}

    legacy.__module__ = "app.api.legacy.test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/test/golden")).status_code == 200
        assert (await client.get("/api/test/legacy")).status_code == 200

    assert (
        await _find_counter_value(
            redis_client,
            group="golden",
            method="GET",
            path="/api/test/golden",
        )
        == 1
    )
    assert (
        await _find_counter_value(
            redis_client,
            group="legacy",
            method="GET",
            path="/api/test/legacy",
        )
        == 1
    )

    assert await _find_status_counter_value(redis_client, group="golden", status_code=200) == 1
    assert await _find_status_counter_value(redis_client, group="legacy", status_code=200) == 1


async def test_route_metrics_disabled_does_not_write(monkeypatch) -> None:
    monkeypatch.delenv(ENABLE_ROUTE_METRICS_ENV, raising=False)

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    app = FastAPI()
    app.add_middleware(RouteMetricsMiddleware)
    app.state.route_metrics_redis = redis_client

    @app.get("/api/test/golden")
    async def handler() -> dict[str, bool]:
        return {"ok": True}

    handler.__module__ = "app.api.v1.endpoints.test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/test/golden")).status_code == 200

    assert await redis_client.keys(f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:*") == []


async def test_route_metrics_missing_redis_is_best_effort(monkeypatch) -> None:
    monkeypatch.setenv(ENABLE_ROUTE_METRICS_ENV, "1")

    app = FastAPI()
    app.add_middleware(RouteMetricsMiddleware)

    @app.get("/api/test/golden")
    async def handler() -> dict[str, bool]:
        return {"ok": True}

    handler.__module__ = "app.api.v1.endpoints.test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/test/golden")).status_code == 200
