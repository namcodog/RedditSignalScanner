from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class IngestPostsBatchInput:
    community_name: str
    posts: Sequence[dict[str, Any]]


@dataclass(slots=True)
class IngestPostsBatchResult:
    new: int
    updated: int
    duplicates: int

    def to_payload(self) -> dict[str, int]:
        return {
            "new": self.new,
            "updated": self.updated,
            "duplicates": self.duplicates,
        }


@dataclass(slots=True)
class IngestPostsBatchDeps:
    execute_dual_write: Callable[[str, Sequence[RedditPost]], Awaitable[tuple[int, int, int]]]


def build_reddit_posts(posts: Sequence[dict[str, Any]]) -> list[RedditPost]:
    reddit_posts: list[RedditPost] = []
    for post in posts:
        reddit_posts.append(
            RedditPost(
                id=post.get("id"),
                title=post.get("title"),
                selftext=post.get("selftext"),
                score=post.get("score"),
                num_comments=post.get("num_comments"),
                created_utc=float(post.get("created_utc", 0)),
                author=post.get("author"),
                url=post.get("url"),
                permalink=post.get("permalink"),
                subreddit=post.get("subreddit"),
            )
        )
    return reddit_posts


async def ingest_posts_batch(
    *,
    workflow_input: IngestPostsBatchInput,
    deps: IngestPostsBatchDeps,
) -> IngestPostsBatchResult:
    if not workflow_input.posts:
        return IngestPostsBatchResult(new=0, updated=0, duplicates=0)

    reddit_posts = build_reddit_posts(workflow_input.posts)
    new_count, updated_count, duplicate_count = await deps.execute_dual_write(
        workflow_input.community_name,
        reddit_posts,
    )
    return IngestPostsBatchResult(
        new=new_count,
        updated=updated_count,
        duplicates=duplicate_count,
    )


__all__ = [
    "IngestPostsBatchDeps",
    "IngestPostsBatchInput",
    "IngestPostsBatchResult",
    "build_reddit_posts",
    "ingest_posts_batch",
]
