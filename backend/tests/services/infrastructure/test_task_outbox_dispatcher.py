from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.infrastructure import task_outbox_dispatcher as dispatcher


@pytest.mark.asyncio
async def test_dispatch_pending_task_outbox_reports_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value="reddit_signal_scanner_dev")

    monkeypatch.setattr(
        dispatcher,
        "fetch_pending_task_outbox",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        dispatcher,
        "resolve_outbox_env_fingerprint",
        lambda: "dev-fingerprint",
    )

    result = await dispatcher.dispatch_pending_task_outbox(
        session,
        batch_size=10,
        max_retries=5,
        send_task=MagicMock(),
        execute_task_name="tasks.crawler.execute_target",
        comments_backfill_queue="comments_queue",
        backfill_posts_queue="backfill_posts_queue_v2",
    )

    assert result.as_dict() == {
        "status": "idle",
        "selected": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
    }


@pytest.mark.asyncio
async def test_dispatch_pending_task_outbox_marks_failed_on_missing_target_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value="reddit_signal_scanner_dev")
    mark_failed = AsyncMock(return_value="failed")
    send_task = MagicMock()

    monkeypatch.setattr(
        dispatcher,
        "fetch_pending_task_outbox",
        AsyncMock(return_value=[{"id": "outbox-1", "payload": {"queue": "comments_queue"}}]),
    )
    monkeypatch.setattr(
        dispatcher,
        "mark_task_outbox_failed",
        mark_failed,
    )
    monkeypatch.setattr(
        dispatcher,
        "resolve_outbox_env_fingerprint",
        lambda: "dev-fingerprint",
    )

    result = await dispatcher.dispatch_pending_task_outbox(
        session,
        batch_size=10,
        max_retries=5,
        send_task=send_task,
        execute_task_name="tasks.crawler.execute_target",
        comments_backfill_queue="comments_queue",
        backfill_posts_queue="backfill_posts_queue_v2",
    )

    assert result.status == "failed"
    assert result.failed == 1
    assert result.sent == 0
    send_task.assert_not_called()
    mark_failed.assert_awaited_once()
