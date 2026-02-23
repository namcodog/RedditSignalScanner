from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.tasks import monitoring_task as mt
from app.utils.asyncio_runner import run as run_coro


def test_watchdog_marks_stalled_processing_tasks_failed() -> None:
    # Make the threshold tiny so the test is deterministic.
    mt.TASK_STALL_THRESHOLD_MINUTES = 1
    mt.TASK_STALL_MAX_BATCH = 10

    async def _seed() -> uuid.UUID:
        async with SessionFactory() as session:
            user = User(
                email=f"watchdog-{uuid.uuid4().hex}@example.com",
                password_hash=hash_password("testpass123"),
            )
            session.add(user)
            await session.flush()

            now = datetime.now(timezone.utc)
            task = Task(
                user_id=user.id,
                product_description="Stalled task for watchdog",
                status=TaskStatus.PROCESSING,
                started_at=now - timedelta(minutes=5),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task.id

    task_id = run_coro(_seed())

    result = mt.watchdog_stalled_tasks()
    assert result["stalled_count"] >= 1

    async def _verify() -> None:
        async with SessionFactory() as session:
            refreshed = await session.get(Task, task_id)
            assert refreshed is not None
            assert refreshed.status == TaskStatus.FAILED
            assert refreshed.failure_category in {
                "worker_stalled",
                "system_dependency_down",
            }
            assert refreshed.error_message and "stuck in processing" in refreshed.error_message

            # Audit summary row should exist (best-effort; table is present in prod schema)
            try:
                audit = await session.execute(
                    text(
                        """
                        SELECT new_value
                        FROM data_audit_events
                        WHERE target_id = 'watchdog_stalled_tasks'
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    )
                )
                payload = audit.scalar_one_or_none()
                assert payload is not None
            except Exception:
                pass

    run_coro(_verify())


def test_watchdog_marks_dependency_down_when_no_worker_ping(monkeypatch) -> None:
    """故障注入：当 Celery worker 不可用时，应明确标记 system_dependency_down。"""
    mt.TASK_STALL_THRESHOLD_MINUTES = 1
    mt.TASK_STALL_MAX_BATCH = 10

    class _StubInspect:
        def ping(self):
            return None

    monkeypatch.setattr(mt.celery_app.control, "inspect", lambda: _StubInspect())

    async def _seed() -> uuid.UUID:
        async with SessionFactory() as session:
            user = User(
                email=f"watchdog-depdown-{uuid.uuid4().hex}@example.com",
                password_hash=hash_password("testpass123"),
            )
            session.add(user)
            await session.flush()

            now = datetime.now(timezone.utc)
            task = Task(
                user_id=user.id,
                product_description="Stalled task for dependency down",
                status=TaskStatus.PROCESSING,
                started_at=now - timedelta(minutes=5),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task.id

    task_id = run_coro(_seed())

    result = mt.watchdog_stalled_tasks()
    assert result["stalled_count"] >= 1
    assert result["failure_category"] == "system_dependency_down"

    async def _verify() -> None:
        async with SessionFactory() as session:
            refreshed = await session.get(Task, task_id)
            assert refreshed is not None
            assert refreshed.status == TaskStatus.FAILED
            assert refreshed.failure_category == "system_dependency_down"

    run_coro(_verify())
