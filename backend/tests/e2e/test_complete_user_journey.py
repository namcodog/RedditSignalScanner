from __future__ import annotations

import time
import uuid

import pytest
from httpx import AsyncClient

from .utils import install_fast_analysis, wait_for_task_completion


@pytest.mark.asyncio
async def test_complete_user_journey_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the golden path from registration through report retrieval."""

    install_fast_analysis(monkeypatch)

    email = f"qa-journey-{uuid.uuid4().hex}@example.com"
    password = "QaJourney123!"

    # 1) user registration
    register_start = time.perf_counter()
    register_resp = await client.post("/api/auth/register", json={"email": email, "password": password})
    register_elapsed = time.perf_counter() - register_start
    assert register_resp.status_code == 201
    assert register_elapsed < 0.5  # 30 秒 SLA，测试收紧到 500ms

    # 2) user login
    login_start = time.perf_counter()
    login_resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    login_elapsed = time.perf_counter() - login_start
    assert login_resp.status_code == 200
    assert login_elapsed < 0.5  # 1 秒 SLA
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 3) submit analysis task
    analyze_start = time.perf_counter()
    analyze_resp = await client.post(
        "/api/analyze",
        json={
            "product_description": "AI agent that summarises Reddit market signals for go-to-market teams."
        },
        headers=headers,
    )
    analyze_elapsed = time.perf_counter() - analyze_start
    assert analyze_resp.status_code == 201
    assert analyze_elapsed < 0.5  # 200ms SLA
    task_id = analyze_resp.json()["task_id"]

    # 4) wait for analysis to complete
    completion_start = time.perf_counter()
    status_snapshot = await wait_for_task_completion(client, token, task_id, timeout=30.0)
    completion_elapsed = time.perf_counter() - completion_start
    assert status_snapshot["status"] == "completed"
    assert completion_elapsed < 30.0  # 5 分钟 SLA 缩紧到 30s 以保证测试稳定性

    # 5) retrieve report
    report_start = time.perf_counter()
    report_resp = await client.get(f"/api/report/{task_id}", headers=headers)
    report_elapsed = time.perf_counter() - report_start
    assert report_resp.status_code == 200
    assert report_elapsed < 2.0

    report_payload = report_resp.json()
    executive = report_payload["report"]

    assert len(executive["pain_points"]) >= 5
    assert len(executive["competitors"]) >= 3
    assert len(executive["opportunities"]) >= 3
    assert report_payload["metadata"]["cache_hit_rate"] >= 0.9
    assert report_payload["stats"]["total_mentions"] > 0
