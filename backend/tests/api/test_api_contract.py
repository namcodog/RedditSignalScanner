from __future__ import annotations

from httpx import AsyncClient


async def test_openapi_freezes_api_prefix_contract(client: AsyncClient) -> None:
    """
    保守版门牌契约：对外只认 /api，不提供 /api/v1。

    这个测试的意义（大白话）：
    - 防止我们未来不小心把“门牌前缀”改乱，导致前端/调用方集体报错。
    """
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    payload = resp.json()

    paths = payload.get("paths") or {}
    assert isinstance(paths, dict)

    assert "/api/analyze" in paths
    assert "/api/status/{task_id}" in paths
    assert "/api/analyze/stream/{task_id}" in paths
    assert "/api/report/{task_id}" in paths

    assert not any(str(path).startswith("/api/v1") for path in paths)

