from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_probe_hot_planner_writes_single_target_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import probe_task

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    monkeypatch.setattr(probe_task.celery_app, "send_task", fake_send_task)

    hot_sources = [f"r/s{i}" for i in range(30)]  # should be clamped to 20

    out = await probe_task._plan_probe_hot_target_impl(
        hot_sources=hot_sources,
        posts_per_source=9999,  # clamp to 50
        max_candidate_subreddits=30,
        max_evidence_per_subreddit=3,
        min_score=100,
        min_comments=30,
        max_age_hours=72,
    )

    target_id = str(out.get("target_id") or "")
    crawl_run_id = str(out.get("crawl_run_id") or "")
    assert target_id
    assert crawl_run_id

    assert len(sent) == 1
    assert sent[0]["task_name"] == "tasks.crawler.execute_target"
    assert sent[0]["kwargs"]["queue"] == "probe_queue"
    assert sent[0]["kwargs"]["kwargs"]["target_id"] == target_id

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status, plan_kind, config
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        status, plan_kind, config = row.one()

    assert str(status) == "queued"
    assert str(plan_kind) == "probe"
    assert isinstance(config, dict)
    assert config.get("plan_kind") == "probe"
    assert config.get("target_type") == "subreddit"
    meta = config.get("meta") or {}
    assert meta.get("source") == "hot"
    assert isinstance(meta.get("hot_sources"), list)
    assert len(meta.get("hot_sources") or []) == 20
    assert int(meta.get("posts_per_source") or 0) == 50
    assert int(meta.get("max_candidate_subreddits") or 0) == 30
    assert int(meta.get("max_evidence_per_subreddit") or 0) == 3
    assert int(meta.get("min_score") or 0) == 100
    assert int(meta.get("min_comments") or 0) == 30
    assert int(meta.get("max_age_hours") or 0) == 72

