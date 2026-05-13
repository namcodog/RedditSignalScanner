from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.crawl.incremental_post_persistence_service import (
    DualWriteDeps,
    DualWriteInput,
    execute_dual_write,
)
from app.services.infrastructure.reddit_client import RedditPost


class _FakeNestedTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeAsyncSession:
    def __init__(self) -> None:
        self._in_transaction = False
        self.begin_calls = 0
        self.begin_nested_calls = 0
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def begin(self) -> None:
        self._in_transaction = True
        self.begin_calls += 1

    def begin_nested(self) -> _FakeNestedTransaction:
        self.begin_nested_calls += 1
        return _FakeNestedTransaction()

    async def flush(self) -> None:
        self.flush_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1


def _make_post(post_id: str) -> RedditPost:
    return RedditPost(
        id=post_id,
        title=f"title-{post_id}",
        selftext="body",
        score=1,
        num_comments=0,
        created_utc=1.0,
        subreddit="test",
        author="author",
        url="https://example.com",
        permalink=f"/r/test/{post_id}",
    )


@pytest.mark.asyncio
async def test_execute_dual_write_skips_current_unique_violation() -> None:
    db = _FakeAsyncSession()
    post = _make_post("dup-1")

    async def _raise_unique(_community_name: str, _post: RedditPost) -> tuple[bool, bool]:
        raise IntegrityError(
            "stmt",
            {},
            Exception('duplicate key value violates unique constraint "ux_posts_raw_current"'),
        )

    result = await execute_dual_write(
        write_input=DualWriteInput(community_name="r/test", posts=[post]),
        deps=DualWriteDeps(
            db=db,
            upsert_to_cold_storage=_raise_unique,
            upsert_to_hot_cache=AsyncMock(),
            is_current_unique_violation=lambda exc: "ux_posts_raw_current" in str(exc.orig),
            schedule_posts_latest_refresh=lambda: None,
            enqueue_comment_backfill=lambda *_args: None,
        ),
    )

    assert result.new_count == 0
    assert result.updated_count == 0
    assert result.duplicate_count == 1
    assert db.commit_calls == 2


@pytest.mark.asyncio
async def test_execute_dual_write_triggers_refresh_and_comment_backfill() -> None:
    db = _FakeAsyncSession()
    first_post = _make_post("new-1")
    second_post = _make_post("updated-1")
    scheduled: list[str] = []
    backfill_calls: list[tuple[str, list[str]]] = []

    cold_results = {
        "new-1": (True, False),
        "updated-1": (False, True),
    }

    async def _upsert_cold(_community_name: str, post: RedditPost) -> tuple[bool, bool]:
        return cold_results[post.id]

    hot_cache = AsyncMock()

    result = await execute_dual_write(
        write_input=DualWriteInput(
            community_name="r/test",
            posts=[first_post, second_post],
            trigger_comments_fetch=True,
            refresh_posts_latest_after_write=True,
        ),
        deps=DualWriteDeps(
            db=db,
            upsert_to_cold_storage=_upsert_cold,
            upsert_to_hot_cache=hot_cache,
            is_current_unique_violation=lambda _exc: False,
            schedule_posts_latest_refresh=lambda: scheduled.append("refresh"),
            enqueue_comment_backfill=lambda community_name, posts: backfill_calls.append(
                (community_name, [post.id for post in posts])
            ),
        ),
    )

    assert result.new_count == 1
    assert result.updated_count == 1
    assert result.duplicate_count == 0
    assert hot_cache.await_count == 2
    assert scheduled == ["refresh"]
    assert backfill_calls == [("r/test", ["new-1"])]
