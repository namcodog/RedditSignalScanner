from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.task import Task
from app.models.user import User

settings = get_settings()


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def test_create_analysis_task(client: AsyncClient, db_session: AsyncSession) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash="hashed-password")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {"product_description": "AI helper that summarises product feedback from Reddit."}

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    assert "task_id" in data
    assert data["status"] == "pending"
    assert response.headers["Location"] == data["sse_endpoint"]

    created_at = _parse_iso(data["created_at"])
    estimated = _parse_iso(data["estimated_completion"])
    delta = abs((estimated - created_at) - timedelta(minutes=settings.estimated_processing_minutes))
    assert delta < timedelta(seconds=1)

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.product_description == payload["product_description"].strip()


async def test_create_analysis_task_requires_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analyze",
        json={"product_description": "A valid product description text."},
    )
    assert response.status_code == 401
