from __future__ import annotations

from httpx import AsyncClient


async def test_get_input_guidance(client: AsyncClient) -> None:
    resp = await client.get("/api/guidance/input")
    assert resp.status_code == 200
    data = resp.json()
    # 必备字段
    assert isinstance(data.get("placeholder"), str)
    assert isinstance(data.get("tips"), list)
    assert isinstance(data.get("examples"), list)

