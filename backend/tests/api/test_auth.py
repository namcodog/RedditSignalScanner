from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.models.user import MembershipLevel, User


settings = get_settings()

def _parse_iso(value: str) -> datetime:
    # FastAPI returns ISO strings without timezone suffix if naive; normalise for comparison.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def test_register_user_creates_account(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"register+{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"

    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email.lower()
    assert data["user"]["membership_level"] == MembershipLevel.FREE.value

    expires_at = _parse_iso(data["expires_at"])
    assert expires_at > datetime.now(timezone.utc)

    user_id = uuid.UUID(data["user"]["id"])
    stored = await db_session.get(User, user_id)
    assert stored is not None
    assert stored.email == email.lower()
    assert stored.password_hash != password
    assert stored.created_at.tzinfo is not None
    assert stored.membership_level == MembershipLevel.FREE


async def test_register_user_conflict_returns_409(client: AsyncClient) -> None:
    email = f"conflict+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "SecurePass123!"}

    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


async def test_login_user_success_returns_token(client: AsyncClient) -> None:
    email = f"login+{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"
    await client.post("/api/auth/register", json={"email": email, "password": password})

    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == email.lower()
    assert data["token_type"] == "bearer"
    assert data["user"]["membership_level"] == MembershipLevel.FREE.value
    jwt.decode(data["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def test_login_user_invalid_password(client: AsyncClient) -> None:
    email = f"wrongpass+{uuid.uuid4().hex}@example.com"
    await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123!"})

    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPass456!"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_full_auth_flow_allows_protected_endpoint(client: AsyncClient) -> None:
    email = f"flow+{uuid.uuid4().hex}@example.com"
    password = "SecurePass123!"

    register_resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    register_data = register_resp.json()
    token = register_data["access_token"]
    assert register_data["user"]["membership_level"] == MembershipLevel.FREE.value

    analyze_resp = await client.post(
        "/api/analyze",
        json={"product_description": "Reddit insight assistant for B2B SaaS teams."},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert analyze_resp.status_code == 201
    body = analyze_resp.json()
    assert body["status"] == "pending"
    assert "task_id" in body
    assert "sse_endpoint" in body
