from __future__ import annotations

import asyncio
import statistics
import time
import uuid

import pytest
from httpx import AsyncClient

from .utils import install_fast_analysis, wait_for_task_completion


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(percentile * (len(ordered) - 1)))))
    return ordered[index]


@pytest.mark.asyncio
async def test_performance_under_concurrency(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate concurrent usage and ensure latency stays within SLA."""

    cache_stats: dict[str, int] = {}
    install_fast_analysis(monkeypatch, cache_stats=cache_stats)

    async def _create_user(idx: int) -> tuple[str, str]:
        email = f"perf-user-{idx}-{uuid.uuid4().hex}@example.com"
        token, user_id = await token_factory(password="PerfUser123!", email=email)
        return token, user_id

    users = await asyncio.gather(*[_create_user(i) for i in range(10)])

    async def _submit_task(token: str) -> float:
        headers = {"Authorization": f"Bearer {token}"}
        start = time.perf_counter()
        resp = await client.post(
            "/api/analyze",
            json={"product_description": "Automated Reddit signal discovery for sales teams."},
            headers=headers,
        )
        elapsed = time.perf_counter() - start
        assert resp.status_code == 201
        task_id = resp.json()["task_id"]
        await wait_for_task_completion(client, token, task_id, timeout=20.0)
        return elapsed

    creation_times = await asyncio.gather(*[_submit_task(token) for token, _ in users])
    assert _percentile(list(creation_times), 0.95) < 0.5

    # High load: reuse the first user to dispatch 50 tasks in parallel batches to avoid overwhelming test DB.
    high_load_token = users[0][0]

    async def _submit_high_load(_: int) -> float:
        return await _submit_task(high_load_token)

    high_load_results = await asyncio.gather(*[_submit_high_load(i) for i in range(50)])
    p95_high_load = _percentile(list(high_load_results), 0.95)
    assert p95_high_load < 0.6
    assert statistics.mean(high_load_results) < 0.4

    # Cache hit rate validation (>90%).
    hit_ratio = cache_stats["hits"] / cache_stats["total"] if cache_stats.get("total") else 1.0
    assert hit_ratio >= 0.9
