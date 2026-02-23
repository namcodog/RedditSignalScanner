from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.crawler_runs_service import ensure_crawler_run
from app.services.crawler_run_targets_service import ensure_crawler_run_target
from app.services.task_outbox_service import (
    OUTBOX_EVENT_EXECUTE_TARGET,
    build_task_outbox_event_key,
    ensure_task_outbox_event,
)


@pytest.mark.asyncio
async def test_task_outbox_dispatcher_sends_and_marks_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    subreddit = "r/outbox_target"

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            config={"plan_kind": "backfill_posts"},
        )
        event_key = build_task_outbox_event_key(
            event_type=OUTBOX_EVENT_EXECUTE_TARGET, target_id=target_id
        )
        await ensure_task_outbox_event(
            session,
            event_key=event_key,
            event_type=OUTBOX_EVENT_EXECUTE_TARGET,
            payload={"target_id": target_id, "queue": "backfill_queue"},
        )
        await session.commit()

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    result = await crawler_task._dispatch_task_outbox_impl()
    assert result["sent"] == 1

    assert sent
    assert sent[0]["task_name"] == "tasks.crawler.execute_target"
    assert sent[0]["kwargs"]["kwargs"]["target_id"] == target_id

    async with SessionFactory() as session:
        outbox_row = await session.execute(
            text(
                """
                SELECT status
                FROM task_outbox
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        )
        assert outbox_row.scalar_one() == "sent"
        target_row = await session.execute(
            text(
                """
                SELECT enqueued_at
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        assert target_row.scalar_one_or_none() is not None
