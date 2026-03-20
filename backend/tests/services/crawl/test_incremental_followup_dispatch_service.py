from __future__ import annotations

from app.services.crawl.incremental_followup_dispatch_service import (
    CommentBackfillDispatchInput,
    IncrementalFollowupDispatchDeps,
    IncrementalScoreRefreshInput,
    dispatch_incremental_score_refresh,
    enqueue_comment_backfill,
    schedule_posts_latest_refresh,
)
from app.services.infrastructure.reddit_client import RedditPost


def _make_post(post_id: str, num_comments: int) -> RedditPost:
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


async def test_dispatch_incremental_score_refresh_clamps_limit() -> None:
    scheduled: list[tuple[str, dict[str, object]]] = []

    await dispatch_incremental_score_refresh(
        IncrementalScoreRefreshInput(new_count=10),
        IncrementalFollowupDispatchDeps(
            send_task=lambda task_name, **kwargs: scheduled.append((task_name, kwargs))
        ),
    )

    assert scheduled == [
        ("tasks.analysis.score_new_posts_v1", {"kwargs": {"limit": 200}})
    ]


def test_enqueue_comment_backfill_sorts_and_caps_targets() -> None:
    scheduled: list[tuple[str, dict[str, object]]] = []
    posts = [
        _make_post("p1", 1),
        _make_post("p2", 9),
        _make_post("p3", 4),
    ]

    enqueue_comment_backfill(
        CommentBackfillDispatchInput(
            community_name="r/TestSub",
            posts=posts,
            enabled=True,
            max_posts=2,
            mode="smart_shallow",
            limit=5,
            depth=1,
        ),
        IncrementalFollowupDispatchDeps(
            send_task=lambda task_name, **kwargs: scheduled.append((task_name, kwargs))
        ),
    )

    assert [item[1]["kwargs"]["source_post_id"] for item in scheduled] == ["p2", "p3"]
    assert all(item[0] == "comments.fetch_and_ingest" for item in scheduled)
    assert all(item[1]["kwargs"]["subreddit"] == "r/testsub" for item in scheduled)


def test_schedule_posts_latest_refresh_dispatches_task() -> None:
    scheduled: list[str] = []

    schedule_posts_latest_refresh(
        IncrementalFollowupDispatchDeps(
            send_task=lambda task_name, **_kwargs: scheduled.append(task_name)
        )
    )

    assert scheduled == ["tasks.maintenance.refresh_posts_latest"]
