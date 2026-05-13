from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.utils.subreddit import normalize_subreddit_name


@dataclass(slots=True)
class IncrementalCrawlWorkflowInput:
    community_name: str
    limit: int
    time_filter: str
    sort: str
    start_time: datetime


@dataclass(slots=True)
class IncrementalCrawlWorkflowDeps:
    get_watermark: Callable[[str], Awaitable[datetime | None]]
    fetch_posts: Callable[[str, int, str, str], Awaitable[Any]]
    filter_spam_posts: Callable[[str, list[Any]], list[Any]]
    dual_write: Callable[[str, list[Any]], Awaitable[tuple[int, int, int]]]
    dispatch_score_refresh: Callable[[int], Awaitable[None]]
    update_watermark: Callable[..., Awaitable[None]]
    record_failure_attempt: Callable[[str, datetime], Awaitable[None]]
    record_empty_attempt: Callable[[str, datetime], Awaitable[None]]
    record_crawl_metrics: Callable[..., Awaitable[None]]


@dataclass(slots=True)
class IncrementalCrawlWorkflowResult:
    payload: dict[str, Any]


async def run_incremental_crawl_workflow(
    *,
    workflow_input: IncrementalCrawlWorkflowInput,
    deps: IncrementalCrawlWorkflowDeps,
) -> IncrementalCrawlWorkflowResult:
    community_name = workflow_input.community_name
    start_time = workflow_input.start_time
    watermark = await deps.get_watermark(community_name)

    effective_limit = min(max(1, int(workflow_input.limit)), 100)
    raw_name = normalize_subreddit_name(community_name)

    try:
        fetch_result = await deps.fetch_posts(
            raw_name,
            effective_limit,
            workflow_input.time_filter,
            workflow_input.sort,
        )
        posts = fetch_result[0] if isinstance(fetch_result, tuple) else fetch_result
    except Exception as exc:
        now = datetime.now(timezone.utc)
        await deps.record_failure_attempt(community_name, now)
        return IncrementalCrawlWorkflowResult(
            payload={
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
                "error": str(exc),
            }
        )

    if not posts:
        now = datetime.now(timezone.utc)
        await deps.record_empty_attempt(community_name, now)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        await deps.record_crawl_metrics(
            empty_crawls=1,
            avg_latency_seconds=duration,
        )
        return IncrementalCrawlWorkflowResult(
            payload={
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
            }
        )

    if watermark:
        posts = [post for post in posts if datetime.fromtimestamp(post.created_utc, tz=timezone.utc) > watermark]

    posts = deps.filter_spam_posts(community_name, list(posts))
    if not posts:
        return IncrementalCrawlWorkflowResult(
            payload={
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
            }
        )

    new_count, updated_count, dup_count = await deps.dual_write(
        community_name,
        posts,
    )
    if new_count:
        await deps.dispatch_score_refresh(new_count)

    latest_post = max(posts, key=lambda item: item.created_utc)
    await deps.update_watermark(
        community_name,
        latest_post.id,
        datetime.fromtimestamp(latest_post.created_utc, tz=timezone.utc),
        total_fetched=len(posts),
        new_valid_posts=new_count,
        dedup_rate=(dup_count / len(posts) * 100) if posts else 0.0,
    )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    await deps.record_crawl_metrics(
        successful_crawls=1,
        total_new_posts=new_count,
        total_updated_posts=updated_count,
        total_duplicates=dup_count,
        avg_latency_seconds=duration,
    )
    return IncrementalCrawlWorkflowResult(
        payload={
            "community": community_name,
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "watermark_updated": True,
            "duration_seconds": duration,
        }
    )


__all__ = [
    "IncrementalCrawlWorkflowDeps",
    "IncrementalCrawlWorkflowInput",
    "IncrementalCrawlWorkflowResult",
    "run_incremental_crawl_workflow",
]
