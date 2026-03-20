from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.incremental_runtime_deps_factory import (
    IncrementalRuntimeDepsFactoryInput,
    build_incremental_runtime_deps,
)
from app.services.infrastructure.reddit_client import RedditPost


def _make_post(post_id: str, num_comments: int = 3) -> RedditPost:
    return RedditPost(
        id=post_id,
        title=f"title-{post_id}",
        selftext="body",
        score=1,
        num_comments=num_comments,
        created_utc=1.0,
        subreddit="test",
        author="author",
        url="https://example.com",
        permalink=f"/r/test/{post_id}",
    )


@pytest.mark.asyncio
async def test_incremental_runtime_deps_factory_ensure_author_upserts() -> None:
    db = AsyncMock()
    deps = build_incremental_runtime_deps(
        IncrementalRuntimeDepsFactoryInput(
            db=db,
            send_task=lambda *args, **kwargs: None,
            comments_backfill_enabled=True,
            comments_backfill_max_posts=2,
            comments_backfill_mode="smart_shallow",
            comments_backfill_limit=5,
            comments_backfill_depth=1,
        )
    )

    await deps.ensure_author("u1", "name")
    await deps.ensure_author(None, None)

    assert db.execute.await_count == 1
    sql, params = db.execute.await_args.args
    assert "INSERT INTO authors" in str(sql)
    assert params == {"aid": "u1", "aname": "name"}


@pytest.mark.asyncio
async def test_incremental_runtime_deps_factory_cache_status_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_failure(input_obj, deps):
        captured["failure_input"] = input_obj
        captured["failure_db"] = deps.db

    async def _fake_empty(input_obj, deps):
        captured["empty_input"] = input_obj
        captured["empty_db"] = deps.db

    async def _fake_watermark(input_obj, deps):
        captured["watermark_input"] = input_obj
        captured["watermark_db"] = deps.db

    monkeypatch.setattr(
        "app.services.crawl.incremental_runtime_deps_factory.record_incremental_failure_attempt",
        _fake_failure,
    )
    monkeypatch.setattr(
        "app.services.crawl.incremental_runtime_deps_factory.record_incremental_empty_attempt",
        _fake_empty,
    )
    monkeypatch.setattr(
        "app.services.crawl.incremental_runtime_deps_factory.update_incremental_watermark",
        _fake_watermark,
    )

    db = AsyncMock()
    deps = build_incremental_runtime_deps(
        IncrementalRuntimeDepsFactoryInput(
            db=db,
            send_task=lambda *args, **kwargs: None,
            comments_backfill_enabled=True,
            comments_backfill_max_posts=2,
            comments_backfill_mode="smart_shallow",
            comments_backfill_limit=5,
            comments_backfill_depth=1,
        )
    )
    now = datetime.now(timezone.utc)

    await deps.record_failure_attempt("r/test", now)
    await deps.record_empty_attempt("r/test", now)
    await deps.update_watermark("r/test", "p1", now, 10, 3, 0.2)

    assert captured["failure_db"] is db
    assert captured["failure_input"].community_name == "r/test"
    assert captured["empty_db"] is db
    assert captured["empty_input"].community_name == "r/test"
    assert captured["watermark_db"] is db
    assert captured["watermark_input"].last_seen_post_id == "p1"


@pytest.mark.asyncio
async def test_incremental_runtime_deps_factory_followup_dispatch_uses_send_task() -> None:
    scheduled: list[tuple[str, dict[str, object]]] = []

    deps = build_incremental_runtime_deps(
        IncrementalRuntimeDepsFactoryInput(
            db=AsyncMock(),
            send_task=lambda task_name, **kwargs: scheduled.append((task_name, kwargs)),
            comments_backfill_enabled=True,
            comments_backfill_max_posts=1,
            comments_backfill_mode="smart_shallow",
            comments_backfill_limit=5,
            comments_backfill_depth=1,
        )
    )

    await deps.dispatch_score_refresh(5)
    deps.schedule_posts_latest_refresh()
    deps.enqueue_comment_backfill("r/TestSub", [_make_post("p1", 8), _make_post("p2", 1)])

    assert scheduled[0] == ("tasks.analysis.score_new_posts_v1", {"kwargs": {"limit": 200}})
    assert scheduled[1] == ("tasks.maintenance.refresh_posts_latest", {})
    assert scheduled[2][0] == "comments.fetch_and_ingest"
    assert scheduled[2][1]["kwargs"]["source_post_id"] == "p1"
    assert scheduled[2][1]["kwargs"]["subreddit"] == "r/testsub"
