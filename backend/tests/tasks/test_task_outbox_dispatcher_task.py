from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.infrastructure.task_outbox_service import (
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
    assert result["status"] == "completed"
    assert result["selected"] == 1
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


@pytest.mark.asyncio
async def test_task_outbox_dispatcher_reports_degraded_on_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    crawl_run_id = str(uuid.uuid4())
    ok_target_id = str(uuid.uuid4())
    bad_target_id = str(uuid.uuid4())

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=ok_target_id,
            crawl_run_id=crawl_run_id,
            subreddit="r/outbox_ok",
            status="queued",
            config={"plan_kind": "comments_backfill"},
        )
        await ensure_task_outbox_event(
            session,
            event_key=build_task_outbox_event_key(
                event_type=OUTBOX_EVENT_EXECUTE_TARGET, target_id=ok_target_id
            ),
            event_type=OUTBOX_EVENT_EXECUTE_TARGET,
            payload={"target_id": ok_target_id, "queue": "backfill_queue"},
        )
        await ensure_task_outbox_event(
            session,
            event_key=build_task_outbox_event_key(
                event_type=OUTBOX_EVENT_EXECUTE_TARGET, target_id=bad_target_id
            ),
            event_type=OUTBOX_EVENT_EXECUTE_TARGET,
            payload={"target_id": bad_target_id, "queue": "backfill_queue"},
        )
        await session.commit()

    sent_calls: list[str] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        target_id = str(kwargs["kwargs"]["target_id"])
        if target_id == bad_target_id:
            raise RuntimeError("send failed")
        sent_calls.append(task_name)

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    result = await crawler_task._dispatch_task_outbox_impl()

    assert result["status"] == "degraded"
    assert result["selected"] == 2
    assert result["sent"] == 1
    assert result["failed"] == 1
    assert sent_calls == ["tasks.crawler.execute_target"]


@pytest.mark.asyncio
async def test_task_outbox_dispatcher_reports_failed_when_nothing_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    crawl_run_id = str(uuid.uuid4())
    missing_target_id = str(uuid.uuid4())

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_task_outbox_event(
            session,
            event_key=build_task_outbox_event_key(
                event_type=OUTBOX_EVENT_EXECUTE_TARGET, target_id=missing_target_id
            ),
            event_type=OUTBOX_EVENT_EXECUTE_TARGET,
            payload={"target_id": missing_target_id, "queue": "backfill_queue"},
        )
        await session.commit()

    monkeypatch.setattr(crawler_task.celery_app, "send_task", lambda *args, **kwargs: None)

    result = await crawler_task._dispatch_task_outbox_impl()

    assert result["status"] == "failed"
    assert result["selected"] == 1
    assert result["sent"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 1
