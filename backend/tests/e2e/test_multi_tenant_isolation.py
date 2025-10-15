from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient

from .utils import install_fast_analysis, wait_for_task_completion, issue_expired_token
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_multi_tenant_access_isolated(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fast_analysis(monkeypatch)

    token_a, user_a = await token_factory(password="TenantA@123!", email=f"tenant-a-{uuid.uuid4().hex}@example.com")
    token_b, _ = await token_factory(password="TenantB@123!", email=f"tenant-b-{uuid.uuid4().hex}@example.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    analyze_resp = await client.post(
        "/api/analyze",
        json={"product_description": "Multi-tenant isolation scenario"},
        headers=headers_a,
    )
    assert analyze_resp.status_code == 201
    task_id = analyze_resp.json()["task_id"]

    await wait_for_task_completion(client, token_a, task_id, timeout=20.0)

    # Tenant B should not access Tenant A's resources.
    status_forbidden = await client.get(f"/api/status/{task_id}", headers=headers_b)
    assert status_forbidden.status_code == 403

    report_forbidden = await client.get(f"/api/report/{task_id}", headers=headers_b)
    assert report_forbidden.status_code == 403

    # Tenant A still has access.
    status_ok = await client.get(f"/api/status/{task_id}", headers=headers_a)
    assert status_ok.status_code == 200
    assert status_ok.json()["status"] == "completed"

    # JWT expiry test
    expired_token = issue_expired_token(user_a)
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    status_expired = await client.get(f"/api/status/{task_id}", headers=expired_headers)
    assert status_expired.status_code == 401
