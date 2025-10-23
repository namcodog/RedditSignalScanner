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
from app.models.task import Task, TaskStatus
from app.models.user import User

from app.core.security import hash_password

settings = get_settings()

def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def test_get_status_success(client: AsyncClient, db_session: AsyncSession) -> None:
    user = User(email=f"status+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.flush()
    task = Task(user_id=user.id, product_description="Track Reddit sentiment")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    token = _issue_token(str(user.id))
    response = await client.get(
        f"/api/status/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task.id)
    assert data["status"] == TaskStatus.PENDING.value
    assert data["progress"] == 0
    # 新增字段：用于前端轮询恢复 SSE 连接
    assert data["sse_endpoint"] == f"{settings.sse_base_path}/{task.id}"
    # 兼容字段：别名保持一致
    assert data["percentage"] == 0
    assert data["message"] == "任务排队中"
    assert data["current_step"] == "任务排队中"


async def test_get_status_forbidden(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = User(email=f"owner+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    intruder = User(email=f"intruder+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add_all([owner, intruder])
    await db_session.flush()
    task = Task(user_id=owner.id, product_description="Unauthorized access test")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    token = _issue_token(str(intruder.id))
    response = await client.get(
        f"/api/status/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
