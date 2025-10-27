"""Integration tests for CSV export API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Iterator
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models.insight import Evidence, InsightCard
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module", autouse=True)
def _module_event_loop() -> Iterator[None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        loop.close()


@pytest.mark.asyncio
async def test_export_csv_success(client: AsyncClient, db_session):
    user = User(
        email="export-success@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Collect insights for export",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    card = InsightCard(
        task_id=task.id,
        title="Exportable insight",
        summary="Export summary",
        confidence=0.91,
        time_window_days=14,
        subreddits=["r/productivity"],
    )
    db_session.add(card)
    await db_session.flush()

    evidence = Evidence(
        insight_card_id=card.id,
        post_url="https://reddit.com/r/productivity/comments/123",
        excerpt="Export evidence",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/productivity",
        score=0.88,
    )
    db_session.add(evidence)
    await db_session.commit()

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    response = await client.post(
        "/api/export/csv",
        json={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert f"report_{task.id}" in response.headers.get("content-disposition", "")
    assert "Exportable insight" in response.text


@pytest.mark.asyncio
async def test_export_csv_forbidden_for_other_user(client: AsyncClient, db_session):
    owner = User(
        email="export-owner@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
        membership_level=MembershipLevel.PRO,
    )
    stranger = User(
        email="export-stranger@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add_all([owner, stranger])
    await db_session.flush()

    task = Task(
        user_id=owner.id,
        product_description="Owner task",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()

    settings = get_settings()
    token, _ = create_access_token(stranger.id, email=stranger.email, settings=settings)

    response = await client.post(
        "/api/export/csv",
        json={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_export_csv_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/export/csv",
        json={"task_id": str(uuid4())},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_export_csv_task_not_completed(client: AsyncClient, db_session):
    user = User(
        email="export-pending@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Pending task",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    response = await client.post(
        "/api/export/csv",
        json={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_export_csv_returns_404_when_no_insights(client: AsyncClient, db_session):
    user = User(
        email="export-empty@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="No insights",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    response = await client.post(
        "/api/export/csv",
        json={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
