from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from httpx import AsyncClient

from app.core.config import get_settings


async def test_analyze_api_requires_auth(client: AsyncClient) -> None:
    """Ensure protected endpoints reject requests without a bearer token."""
    response = await client.post(
        "/api/analyze",
        json={"product_description": "Tokenless request should fail"},
    )

    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "not authenticated" in detail.lower()


async def test_analyze_api_accepts_valid_token(
    client: AsyncClient,
    token_factory,
) -> None:
    """Verify a valid JWT enables task creation."""
    access_token, _ = await token_factory()

    response = await client.post(
        "/api/analyze",
        json={
            "product_description": "AI assistant that summarises Reddit feedback for SaaS teams."
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert uuid.UUID(data["task_id"])
    assert data["status"] == "pending"


async def test_multi_tenant_isolation_enforced(
    client: AsyncClient,
    token_factory,
) -> None:
    """Ensure cross-tenant access is rejected with 403 Forbidden."""
    owner_token, _ = await token_factory()
    intruder_token, _ = await token_factory()

    create_response = await client.post(
        "/api/analyze",
        json={
            "product_description": "Owner specific analysis request to validate isolation."
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task_id"]

    intruder_response = await client.get(
        f"/api/status/{task_id}",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert intruder_response.status_code == 403
    assert "not authorised" in intruder_response.json()["detail"].lower()


async def test_expired_token_is_rejected(
    client: AsyncClient,
    token_factory,
) -> None:
    _, user_id = await token_factory()
    settings = get_settings()
    now = datetime.now(timezone.utc)

    expired_token = jwt.encode(
        {
            "sub": user_id,
            "exp": int((now - timedelta(minutes=5)).timestamp()),
            "iat": int((now - timedelta(minutes=10)).timestamp()),
            "iss": settings.app_name,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        f"/api/status/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()
