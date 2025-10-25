"""
验收 posts_raw 冷库 90 天滚动窗口清理任务：
1. 任务已加入 Celery Beat，调度为每日 03:30
2. 实现函数会调用 cleanup_old_posts SQL 函数并传递保留天数
"""
from __future__ import annotations

import pytest
from celery.schedules import crontab  # type: ignore[import-untyped]

from app.core.celery_app import celery_app


def test_cleanup_old_posts_task_scheduled() -> None:
    """验收: 冷库清理任务存在且调度正确。"""
    schedule = celery_app.conf.beat_schedule
    assert "cleanup-old-posts" in schedule

    task = schedule["cleanup-old-posts"]
    assert task["task"] == "tasks.maintenance.cleanup_old_posts"

    task_schedule = task["schedule"]
    assert isinstance(task_schedule, crontab)
    assert task_schedule.minute == {30}
    assert task_schedule.hour == {3}

    options = task.get("options", {})
    assert options.get("queue") == "cleanup_queue"
    assert options.get("expires") == 7200


@pytest.mark.asyncio
async def test_cleanup_old_posts_impl_calls_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    """验收: 实现函数调用 cleanup_old_posts() 并提交事务。"""
    from sqlalchemy.sql.elements import TextClause

    from app.tasks import maintenance_task

    class StubResult:
        def __init__(self, value: int) -> None:
            self._value = value

        def scalar(self) -> int:
            return self._value

    class StubSession:
        def __init__(self) -> None:
            self.statements: list[tuple[TextClause, dict[str, int] | None]] = []
            self.commit_calls = 0

        async def __aenter__(self) -> "StubSession":
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

        async def execute(
            self, statement: TextClause, params: dict[str, int] | None = None
        ) -> StubResult:
            self.statements.append((statement, params))
            return StubResult(value=4)

        async def commit(self) -> None:
            self.commit_calls += 1

    sessions: list[StubSession] = []

    def factory() -> StubSession:
        session = StubSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(maintenance_task, "SessionFactory", factory)

    result = await maintenance_task.cleanup_old_posts_impl(retention_days=45)

    assert result["status"] == "completed"
    assert result["retention_days"] == 45
    assert result["deleted_count"] == 4
    assert "duration_seconds" in result

    assert sessions, "SessionFactory 应该被调用一次"
    session = sessions[0]
    assert session.commit_calls == 1
    assert len(session.statements) == 1

    statement, params = session.statements[0]
    assert "cleanup_old_posts" in str(statement)
    assert params == {"retention_days": 45}
