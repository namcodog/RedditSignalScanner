from __future__ import annotations

from typing import Any

import pytest

from app.services.crawl.ingest_posts_batch_service import (
    IngestPostsBatchDeps,
    IngestPostsBatchInput,
    build_reddit_posts,
    ingest_posts_batch,
)


def test_build_reddit_posts_maps_dicts_to_reddit_post_objects() -> None:
    posts = build_reddit_posts(
        [
            {
                "id": "p1",
                "title": "hello",
                "selftext": "body",
                "score": 12,
                "num_comments": 4,
                "created_utc": 123.0,
                "author": "u1",
                "url": "https://example.com/1",
                "permalink": "/r/test/comments/p1",
                "subreddit": "r/test",
            }
        ]
    )

    assert len(posts) == 1
    assert posts[0].id == "p1"
    assert posts[0].title == "hello"
    assert posts[0].selftext == "body"
    assert posts[0].num_comments == 4


@pytest.mark.asyncio
async def test_ingest_posts_batch_short_circuits_empty_batch() -> None:
    async def _unexpected(*_args: Any, **_kwargs: Any) -> tuple[int, int, int]:
        raise AssertionError("dual write should not run")

    result = await ingest_posts_batch(
        workflow_input=IngestPostsBatchInput(
            community_name="r/test",
            posts=[],
        ),
        deps=IngestPostsBatchDeps(execute_dual_write=_unexpected),
    )

    assert result.to_payload() == {"new": 0, "updated": 0, "duplicates": 0}


@pytest.mark.asyncio
async def test_ingest_posts_batch_delegates_to_dual_write() -> None:
    captured: dict[str, Any] = {}

    async def _dual_write(community_name: str, posts: Any) -> tuple[int, int, int]:
        captured["community_name"] = community_name
        captured["posts"] = list(posts)
        return (2, 1, 3)

    result = await ingest_posts_batch(
        workflow_input=IngestPostsBatchInput(
            community_name="r/test",
            posts=[
                {
                    "id": "p1",
                    "title": "hello",
                    "selftext": "body",
                    "score": 12,
                    "num_comments": 4,
                    "created_utc": 123.0,
                    "author": "u1",
                    "url": "https://example.com/1",
                    "permalink": "/r/test/comments/p1",
                    "subreddit": "r/test",
                }
            ],
        ),
        deps=IngestPostsBatchDeps(execute_dual_write=_dual_write),
    )

    assert captured["community_name"] == "r/test"
    assert len(captured["posts"]) == 1
    assert captured["posts"][0].id == "p1"
    assert result.to_payload() == {"new": 2, "updated": 1, "duplicates": 3}
