from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.facts_run_log import FactsRunLog
from app.models.facts_snapshot import FactsSnapshot
from app.models.task import Task
from app.models.user import User
from app.tasks import monitoring_task


def test_monitor_facts_audit_cleanup_reports_backlog_and_last_run(
    monkeypatch,
) -> None:
    now = datetime.now(timezone.utc)

    async def _prepare() -> None:
        async with SessionFactory() as session:
            user = User(
                email=f"facts-monitor-{uuid.uuid4().hex}@example.com",
                password_hash=hash_password("SecurePass123!"),
            )
            session.add(user)
            await session.flush()

            task = Task(
                user_id=user.id,
                product_description="Facts audit monitor test task.",
                mode="market_insight",
                audit_level="gold",
            )
            session.add(task)
            await session.flush()

            session.add(
                FactsSnapshot(
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
            )
            session.add(
                FactsRunLog(
                    task_id=task.id,
                    audit_level="lab",
                    status="ok",
                    validator_level="info",
                    retention_days=30,
                    expires_at=now - timedelta(days=1),
                    summary={"posts_analyzed": 0},
                )
            )
            await session.execute(
                text(
                    """
                    INSERT INTO maintenance_audit
                    (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                    VALUES
                    (:task_name, :source, :triggered_by, :started_at, :ended_at, :affected_rows, :sample_ids, CAST(:extra AS JSONB))
                    """
                ),
                {
                    "task_name": "cleanup_expired_facts_audit",
                    "source": "pytest",
                    "triggered_by": "tester",
                    "started_at": now - timedelta(hours=1),
                    "ended_at": now - timedelta(minutes=50),
                    "affected_rows": 2,
                    "sample_ids": [1, 2],
                    "extra": json.dumps(
                        {
                            "deleted_snapshots": 1,
                            "deleted_run_logs": 1,
                            "batches": 1,
                        }
                    ),
                },
            )
            await session.commit()

    asyncio.run(_prepare())

    alerts: list[tuple[str, str]] = []
    dashboards: list[dict[str, object]] = []
    monkeypatch.setattr(monitoring_task, "_send_alert", lambda level, message: alerts.append((level, message)))
    monkeypatch.setattr(
        monitoring_task,
        "_update_dashboard",
        lambda _settings, values: dashboards.append(values),
    )
    monkeypatch.setenv("ENABLE_FACTS_AUDIT_CLEANUP", "1")
    monkeypatch.setattr(monitoring_task, "FACTS_AUDIT_BACKLOG_THRESHOLD", 0)
    monkeypatch.setattr(monitoring_task, "FACTS_AUDIT_MAX_STALE_HOURS", 24)

    payload = monitoring_task.monitor_facts_audit_cleanup()

    assert payload["expired_snapshots"] == 1
    assert payload["expired_run_logs"] == 1
    assert payload["backlog_total"] == 2
    assert payload["last_cleanup_deleted_snapshots"] == 1
    assert payload["last_cleanup_deleted_run_logs"] == 1
    assert payload["status"] == "ok"
    assert alerts
    assert dashboards
    assert "facts_audit_cleanup" in dashboards[0]
