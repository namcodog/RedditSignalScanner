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
from app.api.v1.endpoints import tasks as tasks_endpoint
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.infrastructure.task_status_cache import TaskStatusPayload

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


async def test_get_status_keeps_cached_stage_metadata_after_completion(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    user = User(email=f"status-rich+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.flush()
    task = Task(
        user_id=user.id,
        product_description="Track Reddit sentiment",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async def fake_get_status(task_id: str, session=None, *, repopulate: bool = True):
        return TaskStatusPayload(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=78,
            message="Task processing",
            stage="warmup",
            blocked_reason="insufficient_samples",
            next_action="auto_rerun_scheduled",
            details={"next_retry_at": "2026-03-19T12:00:00+00:00"},
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def fake_set_status(payload: TaskStatusPayload, ttl_seconds: int = 3600) -> None:
        return None

    monkeypatch.setattr(tasks_endpoint.STATUS_CACHE, "get_status", fake_get_status)
    monkeypatch.setattr(tasks_endpoint.STATUS_CACHE, "set_status", fake_set_status)

    token = _issue_token(str(user.id))
    response = await client.get(
        f"/api/status/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TaskStatus.COMPLETED.value
    assert data["stage"] == "warmup"
    assert data["blocked_reason"] == "insufficient_samples"
    assert data["next_action"] == "auto_rerun_scheduled"
    assert data["details"]["next_retry_at"] == "2026-03-19T12:00:00+00:00"
