from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_backfill_bootstrap_planner_delegates_to_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl.planner_workflow import PlannerWorkflowResult
    from app.tasks import crawler_task

    captured: dict[str, object] = {}

    async def fake_workflow(params, *, deps):
        captured["params"] = params
        captured["deps"] = deps
        return PlannerWorkflowResult(
            status="planned",
            inserted=1,
            enqueued=1,
            run_id="test-backfill-run",
        )

    monkeypatch.setattr(crawler_task, "plan_backfill_bootstrap_workflow", fake_workflow)
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_MAX_TARGETS", "5")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_POSTS_LIMIT", "123")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_WINDOW_DAYS", "365")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_COOLDOWN_MINUTES", "0")
    monkeypatch.setenv("BACKFILL_ERROR_COOLDOWN_MINUTES", "360")

    result = await crawler_task._plan_backfill_bootstrap_impl()

    assert result == {
        "status": "planned",
        "inserted": 1,
        "enqueued": 1,
        "run_id": "test-backfill-run",
    }
    params = captured["params"]
    assert params.max_targets == 5
    assert params.posts_limit == 123
    assert params.window_days == 365
    assert params.cooldown_minutes == 0
    assert params.error_cooldown_minutes == 360
    assert params.queue == crawler_task.BACKFILL_POSTS_QUEUE
    assert isinstance(params.now, datetime)
    assert params.now.tzinfo == timezone.utc
    deps = captured["deps"]
    assert deps.session_factory is crawler_task.SessionFactory
    assert deps.ensure_crawler_run is crawler_task.ensure_crawler_run
    assert deps.log_swallowed_exception is crawler_task._log_swallowed_exception
    assert deps.queue_deps.session_factory is crawler_task.SessionFactory


@pytest.mark.asyncio
async def test_backfill_bootstrap_planner_skips_when_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    @asynccontextmanager
    async def fake_lock(_key: str):
        yield False

    monkeypatch.setattr(crawler_task, "_planner_lock", fake_lock)

    result = await crawler_task._plan_backfill_bootstrap_impl()

    assert result["status"] == "locked"
    assert result["inserted"] == 0
    assert result["enqueued"] == 0
