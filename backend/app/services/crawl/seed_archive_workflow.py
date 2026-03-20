from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.infrastructure.reddit_client import RedditAPIClient


@dataclass(slots=True)
class SeedArchiveWorkflowInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class SeedArchiveWorkflowDeps:
    crawler_factory: Callable[..., IncrementalCrawler]
    now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


@dataclass(slots=True)
class SeedArchiveWorkflowResult:
    payload: dict[str, object]


def _resolve_seed_archive_mode(plan_kind: str) -> tuple[str, str]:
    sort = "top"
    time_filter = "year"
    if plan_kind == "seed_top_all":
        time_filter = "all"
    elif plan_kind == "seed_controversial_year":
        sort = "controversial"
        time_filter = "year"
    return sort, time_filter


async def execute_seed_archive_workflow(
    *,
    workflow_input: SeedArchiveWorkflowInput,
    deps: SeedArchiveWorkflowDeps,
) -> SeedArchiveWorkflowResult:
    plan = workflow_input.plan
    max_posts = int(plan.limits.posts_limit or 1000)
    max_posts = max(1, min(1000, max_posts))
    cursor_after = str(plan.meta.get("cursor_after") or "").strip() or None
    sort, time_filter = _resolve_seed_archive_mode(plan.plan_kind)

    crawler = deps.crawler_factory(
        db=workflow_input.session,
        reddit_client=workflow_input.reddit_client,
        crawl_run_id=workflow_input.crawl_run_id,
        community_run_id=workflow_input.community_run_id,
        source_track=str(plan.plan_kind),
        refresh_posts_latest_after_write=False,
        enable_comments_backfill=True,
        comments_backfill_mode="smart_shallow",
        comments_backfill_limit=50,
        comments_backfill_depth=2,
    )

    start_time = deps.now_provider()
    posts: list[Any] = []
    next_after = cursor_after
    while len(posts) < max_posts:
        batch_limit = min(100, max_posts - len(posts))
        batch, batch_after = await workflow_input.reddit_client.fetch_subreddit_posts(
            plan.target_value,
            limit=batch_limit,
            time_filter=time_filter,
            sort=sort,
            after=next_after,
        )
        if not batch:
            break
        posts.extend(batch)
        if not batch_after:
            next_after = None
            break
        next_after = batch_after

    finished_at = deps.now_provider()
    duration = (finished_at - start_time).total_seconds()
    if not posts:
        return SeedArchiveWorkflowResult(
            payload={
                "plan_kind": plan.plan_kind,
                "status": "completed",
                "total_fetched": 0,
                "unique_posts": 0,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "duration_seconds": duration,
                "max_seen_created_at": None,
                "min_seen_created_at": None,
            }
        )

    new_count, updated_count, dup_count = await crawler._dual_write(
        plan.target_value,
        posts,
        trigger_comments_fetch=True,
    )

    max_post = max(posts, key=lambda post: post.created_utc)
    min_post = min(posts, key=lambda post: post.created_utc)
    max_seen = datetime.fromtimestamp(max_post.created_utc, tz=timezone.utc)
    min_seen = datetime.fromtimestamp(min_post.created_utc, tz=timezone.utc)

    return SeedArchiveWorkflowResult(
        payload={
            "plan_kind": plan.plan_kind,
            "status": "completed",
            "total_fetched": len(posts),
            "unique_posts": len(posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "duration_seconds": duration,
            "max_seen_created_at": max_seen.isoformat(),
            "min_seen_created_at": min_seen.isoformat(),
        }
    )


__all__ = [
    "SeedArchiveWorkflowDeps",
    "SeedArchiveWorkflowInput",
    "SeedArchiveWorkflowResult",
    "execute_seed_archive_workflow",
]
