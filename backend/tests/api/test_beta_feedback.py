from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
async def test_submit_feedback_success(client: AsyncClient, token_factory, db_session: AsyncSession) -> None:
    token, user_id = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}

    # Create a task for this user
    task = Task(user_id=uuid.UUID(user_id), product_description="A valid description for analysis")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    payload = {
        "task_id": str(task.id),
        "satisfaction": 4,
        "missing_communities": ["r/example1", "r/example2"],
        "comments": "Looks good overall"
    }

    resp = await client.post("/api/beta/feedback", headers=headers, json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["task_id"] == str(task.id)
    assert data["satisfaction"] == 4

    # Verify persisted
    from app.models.beta_feedback import BetaFeedback
    row = (
        await db_session.execute(
            select(BetaFeedback).where(BetaFeedback.task_id == task.id)
        )
    ).scalar_one()
    assert row.user_id == uuid.UUID(user_id)
    assert row.satisfaction == 4
    assert row.missing_communities == ["r/example1", "r/example2"]


@pytest.mark.asyncio
async def test_submit_feedback_404_on_missing_task(client: AsyncClient, token_factory) -> None:
    token, _uid = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "task_id": str(uuid.uuid4()),
        "satisfaction": 5,
        "missing_communities": [],
        "comments": "no task"
    }
    resp = await client.post("/api/beta/feedback", headers=headers, json=payload)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback_forbidden_if_task_not_owned(client: AsyncClient, token_factory, db_session: AsyncSession) -> None:
    token1, user1 = await token_factory()
    token2, user2 = await token_factory()

    # Create task for user1
    task = Task(user_id=uuid.UUID(user1), product_description="A valid task description")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    headers = {"Authorization": f"Bearer {token2}"}
    payload = {
        "task_id": str(task.id),
        "satisfaction": 3,
        "missing_communities": [],
        "comments": "wrong user"
    }
    resp = await client.post("/api/beta/feedback", headers=headers, json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_feedback_unauthenticated_401(client: AsyncClient) -> None:
    payload = {
        "task_id": str(uuid.uuid4()),
        "satisfaction": 3,
        "missing_communities": [],
        "comments": "no auth"
    }
    resp = await client.post("/api/beta/feedback", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_list_feedback(client: AsyncClient, token_factory, db_session: AsyncSession) -> None:
    # Create admin and normal user
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    from app.core.config import get_settings

    # Override admin allowlist
    overridden = get_settings().model_copy(update={"admin_emails_raw": admin_email})
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        user_token, user_id = await token_factory()
        # Create a task for normal user and a feedback
        task = Task(user_id=uuid.UUID(user_id), product_description="A valid task description")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        headers_user = {"Authorization": f"Bearer {user_token}"}
        await client.post(
            "/api/beta/feedback",
            headers=headers_user,
            json={
                "task_id": str(task.id),
                "satisfaction": 5,
                "missing_communities": ["r/x"],
                "comments": "great"
            },
        )

        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        resp = await client.get("/api/admin/beta/feedback", headers=headers_admin)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total"] >= 1
        items = body["data"]["items"]
        assert any(it["satisfaction"] == 5 for it in items)
    finally:
        from app.core.config import get_settings as _get
        app.dependency_overrides.pop(_get, None)

