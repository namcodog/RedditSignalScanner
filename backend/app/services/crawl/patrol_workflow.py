from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.infrastructure.reddit_client import RedditAPIClient


@dataclass(slots=True)
class PatrolWorkflowInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class PatrolWorkflowDeps:
    crawler_factory: Callable[..., IncrementalCrawler]


@dataclass(slots=True)
class PatrolWorkflowResult:
    payload: dict[str, object]


async def execute_patrol_workflow(
    *,
    workflow_input: PatrolWorkflowInput,
    deps: PatrolWorkflowDeps,
) -> PatrolWorkflowResult:
    plan = workflow_input.plan
    posts_limit = int(plan.limits.posts_limit or 80)
    posts_limit = max(1, min(100, posts_limit))
    raw_time_filter = str(plan.meta.get("time_filter") or "day").strip().lower()
    time_filter = raw_time_filter if raw_time_filter in {"hour", "day"} else "day"
    sort = str(plan.meta.get("sort") or "top")
    hot_cache_ttl_hours = int(plan.meta.get("hot_cache_ttl_hours") or 4320)

    crawler = deps.crawler_factory(
        db=workflow_input.session,
        reddit_client=workflow_input.reddit_client,
        hot_cache_ttl_hours=hot_cache_ttl_hours,
        crawl_run_id=workflow_input.crawl_run_id,
        community_run_id=workflow_input.community_run_id,
        source_track="incremental",
    )
    payload = await crawler.crawl_community_incremental(
        plan.target_value,
        limit=posts_limit,
        time_filter=time_filter,
        sort=sort,
    )
    return PatrolWorkflowResult(payload=dict(payload))


__all__ = [
    "PatrolWorkflowDeps",
    "PatrolWorkflowInput",
    "PatrolWorkflowResult",
    "execute_patrol_workflow",
]
