from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.models.user import MembershipLevel


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    email = f"complete-register-{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "SecurePass123!"}

    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == email.lower()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["membership_level"] == MembershipLevel.FREE.value


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    email = f"complete-duplicate-{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "SecurePass123!"}

    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    email = f"complete-login-{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"
    await client.post("/api/auth/register", json={"email": email, "password": password})

    response = await client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == email.lower()
    assert body["user"]["membership_level"] == MembershipLevel.FREE.value
    jwt.decode(
        body["access_token"],
        get_settings().jwt_secret,
        algorithms=[get_settings().jwt_algorithm],
    )


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    email = f"complete-wrong-{uuid.uuid4().hex}@example.com"
    await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123!"})

    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_token_expiration(client: AsyncClient, token_factory) -> None:
    _, user_id = await token_factory()
    settings = get_settings()
    now = datetime.now(timezone.utc)

    expired_token = jwt.encode(
        {
            "sub": user_id,
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "iat": int((now - timedelta(minutes=2)).timestamp()),
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


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient, token_factory) -> None:
    owner_token, _ = await token_factory()
    intruder_token, _ = await token_factory()

    create_response = await client.post(
        "/api/analyze",
        json={"product_description": "Owner request - tenant isolation verification."},
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


@pytest.mark.asyncio
async def test_register_then_create_task(client: AsyncClient) -> None:
    email = f"register-flow-{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"
    register = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201
    register_data = register.json()
    assert register_data["user"]["membership_level"] == MembershipLevel.FREE.value
    token = register_data["access_token"]

    response = await client.post(
        "/api/analyze",
        json={"product_description": "Reddit research assistant for workflow automation."},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data


@pytest.mark.asyncio
async def test_create_task_falls_back_to_email_lookup(client: AsyncClient) -> None:
    email = f"register-fallback-{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"
    register = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201
    original = register.json()
    assert original["user"]["membership_level"] == MembershipLevel.FREE.value

    settings = get_settings()
    fake_subject = str(uuid.uuid4())
    forged_token = jwt.encode(
        {
            "sub": fake_subject,
            "email": original["user"]["email"],
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "iss": settings.app_name,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.post(
        "/api/analyze",
        json={"product_description": "Product research assistant that syncs Reddit insights."},
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 201
    assert "task_id" in response.json()
