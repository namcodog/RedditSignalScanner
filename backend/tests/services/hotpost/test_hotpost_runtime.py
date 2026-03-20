from __future__ import annotations

from typing import Any

import pytest

from app.services.hotpost.hotpost_runtime import (
    fetch_hotpost_comments,
    search_hotpost_subreddit_posts,
)
from app.services.infrastructure.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_search_hotpost_subreddit_posts_paginates_and_counts_calls() -> None:
    budget_calls: list[int] = []
    page_calls: list[str | None] = []

    async def _acquire_rate_budget(*, cost: int, queue_tracker: object | None = None) -> None:
        del queue_tracker
        budget_calls.append(cost)

    async def _search_page(
        subreddit: str,
        query: str,
        *,
        limit: int,
        sort: str,
        time_filter: str,
        after: str | None,
    ) -> tuple[list[RedditPost], str | None]:
        del subreddit, query, limit, sort, time_filter
        page_calls.append(after)
        if after is None:
            return [
                RedditPost(
                    id="p1",
                    subreddit="r/test",
                    title="a",
                    selftext="",
                    author="u1",
                    score=1,
                    num_comments=1,
                    created_utc=1.0,
                    permalink="/r/test/comments/p1",
                    url="https://reddit.com/p1",
                )
            ], "after-1"
        return [
            RedditPost(
                id="p2",
                subreddit="r/test",
                title="b",
                selftext="",
                author="u2",
                score=2,
                num_comments=2,
                created_utc=2.0,
                permalink="/r/test/comments/p2",
                url="https://reddit.com/p2",
            )
        ], None

    posts, calls = await search_hotpost_subreddit_posts(
        "test",
        "robot vacuum",
        sort="top",
        time_filter="all",
        max_posts=2,
        queue_tracker=None,
        acquire_rate_budget=_acquire_rate_budget,
        search_subreddit_page=_search_page,
    )

    assert [post.id for post in posts] == ["p1", "p2"]
    assert calls == 2
    assert budget_calls == [1, 1]
    assert page_calls == [None, "after-1"]


@pytest.mark.asyncio
async def test_fetch_hotpost_comments_trims_and_limits() -> None:
    budget_calls: list[int] = []

    async def _acquire_rate_budget(*, cost: int, queue_tracker: object | None = None) -> None:
        del queue_tracker
        budget_calls.append(cost)

    async def _fetch_post_comments(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return [
            {"body": "x" * 500, "score": 10},
            {"body": "y" * 450, "score": 5},
            {"body": "z" * 10, "score": 1},
            {"body": "extra", "score": 0},
        ]

    comments = await fetch_hotpost_comments(
        "abc",
        queue_tracker=None,
        acquire_rate_budget=_acquire_rate_budget,
        fetch_post_comments=_fetch_post_comments,
    )

    assert budget_calls == [1]
    assert len(comments) == 3
    assert len(comments[0]["body"]) == 400
    assert len(comments[1]["body"]) == 400
    assert len(comments[2]["body"]) == 10
