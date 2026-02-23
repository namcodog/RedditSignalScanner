from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.facts_run_log import FactsRunLog
from app.models.facts_snapshot import FactsSnapshot
from app.models.task import Task
from app.models.user import User
from app.tasks.maintenance_task import cleanup_expired_facts_audit_impl


def test_cleanup_facts_audit_task_scheduled() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "cleanup-expired-facts-audit" in schedule
    task = schedule["cleanup-expired-facts-audit"]
    assert task["task"] == "tasks.maintenance.cleanup_expired_facts_audit"
    assert task.get("options", {}).get("queue") == "cleanup_queue"


@pytest.mark.asyncio
async def test_cleanup_expired_facts_audit_removes_expired_rows() -> None:
    now = datetime.now(timezone.utc)

    async with SessionFactory() as session:
        user = User(
            email=f"facts-clean-{uuid.uuid4().hex}@example.com",
            password_hash=hash_password("SecurePass123!"),
        )
        session.add(user)
        await session.flush()

        task = Task(
            user_id=user.id,
            product_description="Facts cleanup test task.",
            mode="market_insight",
            audit_level="gold",
        )
        session.add(task)
        await session.flush()

        snapshot_expired = FactsSnapshot(
            task_id=task.id,
            schema_version="2.0",
            v2_package={"schema_version": "2.0"},
            quality={"tier": "A_full"},
            passed=True,
            tier="A_full",
            audit_level="gold",
            status="ok",
            validator_level="info",
            retention_days=90,
            expires_at=now - timedelta(days=1),
        )
        snapshot_valid = FactsSnapshot(
            task_id=task.id,
            schema_version="2.0",
            v2_package={"schema_version": "2.0"},
            quality={"tier": "A_full"},
            passed=True,
            tier="A_full",
            audit_level="gold",
            status="ok",
            validator_level="info",
            retention_days=90,
            expires_at=now + timedelta(days=1),
        )
        run_log_expired = FactsRunLog(
            task_id=task.id,
            audit_level="lab",
            status="ok",
            validator_level="info",
            retention_days=30,
            expires_at=now - timedelta(days=1),
            summary={"posts_analyzed": 0},
        )
        run_log_valid = FactsRunLog(
            task_id=task.id,
            audit_level="lab",
            status="ok",
            validator_level="info",
            retention_days=30,
            expires_at=now + timedelta(days=1),
            summary={"posts_analyzed": 0},
        )
        session.add_all(
            [snapshot_expired, snapshot_valid, run_log_expired, run_log_valid]
        )
        await session.commit()

    result = await cleanup_expired_facts_audit_impl(
        batch_size=10, max_batches=5, skip_guard=True
    )
    assert result["deleted_snapshots"] == 1
    assert result["deleted_run_logs"] == 1

    async with SessionFactory() as session:
        snapshots = await session.execute(
            select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
        )
        assert len(snapshots.scalars().all()) == 1
        run_logs = await session.execute(
            select(FactsRunLog).where(FactsRunLog.task_id == task.id)
        )
        assert len(run_logs.scalars().all()) == 1
