from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_probe_search_planner_writes_queued_target_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import probe_task

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    monkeypatch.setattr(probe_task.celery_app, "send_task", fake_send_task)

    out = await probe_task._plan_probe_search_target_impl(
        query="shopify refund",
        posts_limit=9999,  # should be clamped to 100
        max_evidence_posts=9999,  # should be clamped to posts_limit
        max_discovered_communities=9999,  # should be clamped to 200
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
    assert config.get("target_type") == "query"
    meta = config.get("meta") or {}
    assert meta.get("source") == "search"
    assert int((config.get("limits") or {}).get("posts_limit") or 0) == 100
    assert int(meta.get("max_evidence_posts") or 0) == 100
    assert int(meta.get("max_discovered_communities") or 0) == 200

