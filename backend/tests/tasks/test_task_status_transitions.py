from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.tasks import analysis_task


@pytest.mark.asyncio
async def test_mark_processing_rejects_illegal_transition(db_session):
    user = User(
        email=f"status-guard-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="Status machine guard",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    with pytest.raises(ValueError):
        await analysis_task._mark_processing(task.id, retries=0)


@pytest.mark.asyncio
async def test_mark_failed_rejects_illegal_transition(db_session):
    user = User(
        email=f"status-failed-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="Status machine guard",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    with pytest.raises(ValueError):
        await analysis_task._mark_failed(
            task.id,
            "failure",
            failure_category="system_error",
            retries=1,
            reached_dead_letter=False,
        )


@pytest.mark.asyncio
async def test_mark_pending_retry_rejects_from_completed(db_session):
    user = User(
        email=f"status-retry-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="Retry status guard",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    with pytest.raises(ValueError):
        await analysis_task._mark_pending_retry(task.id, retries=1)
