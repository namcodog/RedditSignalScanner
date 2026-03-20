from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Sequence

from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class ComprehensiveCrawlWorkflowInput:
    community_name: str
    time_filter: str
    max_per_strategy: int
    ignore_watermark: bool
    start_time: datetime


@dataclass(slots=True)
class ComprehensiveCrawlWorkflowDeps:
    normalize_subreddit_name: Callable[[str], str]
    get_watermark: Callable[[str], Awaitable[datetime | None]]
    fetch_comprehensive_posts: Callable[[str, str, int], Awaitable[Sequence[RedditPost]]]
    unix_to_datetime: Callable[[float], datetime]
    filter_spam_posts: Callable[[str, Sequence[RedditPost]], list[RedditPost]]
    dual_write: Callable[[str, Sequence[RedditPost]], Awaitable[tuple[int, int, int]]]
    update_watermark: Callable[[str, str, datetime, int, int, float], Awaitable[None]]


@dataclass(slots=True)
class ComprehensiveCrawlWorkflowResult:
    payload: dict[str, Any]


async def run_comprehensive_crawl_workflow(
    *,
    workflow_input: ComprehensiveCrawlWorkflowInput,
    deps: ComprehensiveCrawlWorkflowDeps,
) -> ComprehensiveCrawlWorkflowResult:
    community_name = workflow_input.community_name
    start_time = workflow_input.start_time
    watermark = (
        None
        if workflow_input.ignore_watermark
        else await deps.get_watermark(community_name)
    )

    raw_name = deps.normalize_subreddit_name(community_name)
    try:
        posts = list(
            await deps.fetch_comprehensive_posts(
                raw_name,
                workflow_input.time_filter,
                workflow_input.max_per_strategy,
            )
        )
        total_fetched = len(posts)
    except Exception as exc:
        return ComprehensiveCrawlWorkflowResult(
            payload={
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "total_fetched": 0,
                "unique_posts": 0,
                "duration_seconds": 0,
                "error": str(exc),
            }
        )

    if watermark is not None:
        posts = [
            post
            for post in posts
            if deps.unix_to_datetime(post.created_utc) > watermark
        ]

    filtered_posts = deps.filter_spam_posts(community_name, posts)
    if not filtered_posts:
        return ComprehensiveCrawlWorkflowResult(
            payload={
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "total_fetched": total_fetched,
                "unique_posts": 0,
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        )

    new_count, updated_count, duplicate_count = await deps.dual_write(
        community_name,
        filtered_posts,
    )

    latest_post = max(filtered_posts, key=lambda post: post.created_utc)
    await deps.update_watermark(
        community_name,
        latest_post.id,
        deps.unix_to_datetime(latest_post.created_utc),
        total_fetched,
        new_count,
        (duplicate_count / len(filtered_posts) * 100) if filtered_posts else 0.0,
    )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    return ComprehensiveCrawlWorkflowResult(
        payload={
            "community": community_name,
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": duplicate_count,
            "total_fetched": total_fetched,
            "unique_posts": len(filtered_posts),
            "duration_seconds": duration,
        }
    )


__all__ = [
    "ComprehensiveCrawlWorkflowDeps",
    "ComprehensiveCrawlWorkflowInput",
    "ComprehensiveCrawlWorkflowResult",
    "run_comprehensive_crawl_workflow",
]
