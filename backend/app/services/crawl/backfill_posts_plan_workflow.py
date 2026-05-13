from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.infrastructure.reddit_client import RedditAPIClient


@dataclass(slots=True)
class BackfillPostsPlanWorkflowInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class BackfillPostsPlanWorkflowDeps:
    crawler_factory: Callable[..., IncrementalCrawler]


@dataclass(slots=True)
class BackfillPostsPlanWorkflowResult:
    payload: dict[str, object]


async def execute_backfill_posts_plan_workflow(
    *,
    workflow_input: BackfillPostsPlanWorkflowInput,
    deps: BackfillPostsPlanWorkflowDeps,
) -> BackfillPostsPlanWorkflowResult:
    plan = workflow_input.plan
    if plan.window is None or plan.window.since is None or plan.window.until is None:
        raise ValueError("backfill_posts requires window.since and window.until")

    max_posts = int(plan.limits.posts_limit or 1000)
    cursor_after = str(plan.meta.get("cursor_after") or "").strip() or None
    sort = str(plan.meta.get("sort") or "new")

    crawler = deps.crawler_factory(
        db=workflow_input.session,
        reddit_client=workflow_input.reddit_client,
        crawl_run_id=workflow_input.crawl_run_id,
        community_run_id=workflow_input.community_run_id,
        source_track="backfill_posts",
        refresh_posts_latest_after_write=False,
    )
    payload = await crawler.backfill_posts_window(
        plan.target_value,
        since=plan.window.since,
        until=plan.window.until,
        max_posts=max_posts,
        sort=sort,
        after=cursor_after,
    )
    return BackfillPostsPlanWorkflowResult(payload=dict(payload))


__all__ = [
    "BackfillPostsPlanWorkflowDeps",
    "BackfillPostsPlanWorkflowInput",
    "BackfillPostsPlanWorkflowResult",
    "execute_backfill_posts_plan_workflow",
]
