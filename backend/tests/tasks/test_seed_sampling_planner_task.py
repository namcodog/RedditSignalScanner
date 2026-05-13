from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_seed_sampling_planner_delegates_to_workflow(
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
            inserted=2,
            enqueued=2,
            run_id="test-seed-run",
        )

    monkeypatch.setattr(crawler_task, "plan_seed_sampling_workflow", fake_workflow)
    monkeypatch.setenv("SEED_SAMPLING_COOLDOWN_DAYS", "30")
    monkeypatch.setenv("SEED_SAMPLING_MAX_TARGETS", "10")
    monkeypatch.setenv("SEED_SAMPLING_POSTS_LIMIT", "200")
    monkeypatch.setenv("SEED_SAMPLING_MIN_POSTS", "200")

    result = await crawler_task._plan_seed_sampling_impl()

    assert result == {
        "status": "planned",
        "inserted": 2,
        "enqueued": 2,
        "run_id": "test-seed-run",
    }
    params = captured["params"]
    assert params.cooldown_days == 30
    assert params.max_targets == 10
    assert params.posts_limit == 200
    assert params.min_posts == 200
    assert params.queue == crawler_task.BACKFILL_POSTS_QUEUE
    assert isinstance(params.now, datetime)
    assert params.now.tzinfo == timezone.utc
    deps = captured["deps"]
    assert deps.session_factory is crawler_task.SessionFactory
    assert deps.ensure_crawler_run is crawler_task.ensure_crawler_run
    assert deps.log_swallowed_exception is crawler_task._log_swallowed_exception
    assert deps.queue_deps.session_factory is crawler_task.SessionFactory


@pytest.mark.asyncio
async def test_seed_sampling_planner_skips_when_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    @asynccontextmanager
    async def fake_lock(_key: str):
        yield False

    monkeypatch.setattr(crawler_task, "_planner_lock", fake_lock)

    result = await crawler_task._plan_seed_sampling_impl()

    assert result["status"] == "locked"
    assert result["inserted"] == 0
    assert result["enqueued"] == 0
