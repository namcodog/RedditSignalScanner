from __future__ import annotations

import asyncio
import json

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.models.task import Task
from app.models.user import User
from app.services.task_status_cache import TaskStatusPayload
from app.core.security import hash_password


settings = get_settings()

def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class _StubStatusCache:
    def __init__(self, payloads: list[TaskStatusPayload]) -> None:
        self._payloads = payloads
        self._index = 0

    async def get_status(
        self,
        task_id: str,
        session: AsyncSession | None = None,
    ) -> TaskStatusPayload | None:
        if not self._payloads:
            return None
        if self._index >= len(self._payloads):
            return self._payloads[-1]
        payload = self._payloads[self._index]
        self._index += 1
        return payload


async def _prepare_task(db_session: AsyncSession) -> tuple[User, Task]:
    user = User(email=f"stream+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.flush()
    task = Task(user_id=user.id, product_description="Build SSE stream")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return user, task


async def test_sse_connection_and_completion(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.api.routes import stream

    user, task = await _prepare_task(db_session)
    token = _issue_token(str(user.id))

    payloads = [
        TaskStatusPayload(
            task_id=str(task.id),
            status="processing",
            progress=50,
            message="processing",
            error=None,
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
        TaskStatusPayload(
            task_id=str(task.id),
            status="completed",
            progress=100,
            message="complete",
            error=None,
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
    ]
    monkeypatch.setattr(stream, "STATUS_CACHE", _StubStatusCache(payloads))
    monkeypatch.setattr(stream, "POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(stream, "HEARTBEAT_INTERVAL_SECONDS", 10.0)

    events: list[str] = []
    payloads: list[dict[str, object]] = []
    async with client.stream(
        "GET",
        f"/api/analyze/stream/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    ) as response:
        # Use aiter_bytes() to avoid line buffering issues with SSE
        buffer = ""
        async for chunk in response.aiter_bytes():
            buffer += chunk.decode("utf-8")
            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line.startswith("event:"):
                    events.append(line.split(": ", 1)[1])
                elif line.startswith("data:"):
                    payloads.append(json.loads(line.split(": ", 1)[1]))
                if events and events[-1] == "close":
                    break
            if events and events[-1] == "close":
                break

    assert events[0] == "connected"
    assert "completed" in events
    assert events[-1] == "close"

    # 第一个 payload 应该是进度事件，包含前端期望的字段
    first_payload = next((p for p in payloads if p.get("status") == "processing"), None)
    assert first_payload is not None
    assert first_payload["percentage"] == 50
    assert first_payload["progress"] == 50
    assert first_payload["current_step"] == "processing"
    assert first_payload["error"] is None
    assert "error_message" in first_payload


async def test_sse_heartbeat(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    Validate heartbeat emission by invoking the internal event generator directly
    (avoids httpx.AsyncClient streaming hang on some platforms).
    """
    from app.api.routes import stream

    user, task = await _prepare_task(db_session)

    class _NullCache:
        async def get_status(self, task_id: str, session: AsyncSession | None = None):  # type: ignore[override]
            return None

    # Speed up loop and force heartbeat path
    monkeypatch.setattr(stream, "STATUS_CACHE", _NullCache())
    monkeypatch.setattr(stream, "POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(stream, "HEARTBEAT_INTERVAL_SECONDS", 0.02)

    gen = stream._event_generator(task, db_session)  # type: ignore[attr-defined]

    events: list[str] = []
    deadline = datetime.now(timezone.utc) + timedelta(seconds=1)

    async def _next_chunk() -> str | None:
        try:
            return await gen.__anext__()
        except StopAsyncIteration:
            return None

    while datetime.now(timezone.utc) < deadline and "heartbeat" not in events:
        chunk = await _next_chunk()
        if chunk is None:
            break
        for line in chunk.splitlines():
            line = line.strip()
            if line.startswith("event:"):
                events.append(line.split(": ", 1)[1])
        # safety: do not loop too tight
        await asyncio.sleep(0)

    assert events and events[0] == "connected"
    assert "progress" in events  # baseline event is emitted first for PENDING task
    assert "heartbeat" in events


async def test_sse_permission_denied(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = User(email=f"sse-owner+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    other = User(email=f"sse-other+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add_all([owner, other])
    await db_session.flush()
    task = Task(user_id=owner.id, product_description="Permission check")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    token = _issue_token(str(other.id))
    response = await client.get(
        f"/api/analyze/stream/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
