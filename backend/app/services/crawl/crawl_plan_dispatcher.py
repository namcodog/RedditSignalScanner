from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.backfill_comments_workflow import (
    BackfillCommentsWorkflowDeps,
    BackfillCommentsWorkflowInput,
)
from app.services.crawl.backfill_posts_plan_workflow import (
    BackfillPostsPlanWorkflowDeps,
    BackfillPostsPlanWorkflowInput,
)
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.crawl.patrol_workflow import PatrolWorkflowDeps, PatrolWorkflowInput
from app.services.crawl.probe_workflow import ProbeWorkflowDeps, ProbeWorkflowInput
from app.services.crawl.seed_archive_workflow import (
    SeedArchiveWorkflowDeps,
    SeedArchiveWorkflowInput,
)
from app.services.infrastructure.reddit_client import RedditAPIClient


@dataclass(slots=True)
class CrawlPlanDispatchInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class CrawlPlanDispatchDeps:
    execute_patrol: Callable[
        ...,
        Awaitable[Any],
    ]
    execute_backfill_posts: Callable[
        ...,
        Awaitable[Any],
    ]
    execute_seed_archive: Callable[
        ...,
        Awaitable[Any],
    ]
    execute_probe: Callable[
        ...,
        Awaitable[Any],
    ]
    execute_backfill_comments: Callable[
        ...,
        Awaitable[Any],
    ]
    build_patrol_deps: Callable[[], PatrolWorkflowDeps]
    build_backfill_posts_deps: Callable[[], BackfillPostsPlanWorkflowDeps]
    build_seed_archive_deps: Callable[[], SeedArchiveWorkflowDeps]
    build_probe_deps: Callable[[], ProbeWorkflowDeps]
    build_backfill_comments_deps: Callable[[], BackfillCommentsWorkflowDeps]


async def dispatch_crawl_plan(
    dispatch_input: CrawlPlanDispatchInput,
    deps: CrawlPlanDispatchDeps,
) -> dict[str, object]:
    plan = dispatch_input.plan
    session = dispatch_input.session
    reddit_client = dispatch_input.reddit_client
    crawl_run_id = dispatch_input.crawl_run_id
    community_run_id = dispatch_input.community_run_id

    if plan.plan_kind == "patrol":
        workflow_result = await deps.execute_patrol(
            workflow_input=PatrolWorkflowInput(
                plan=plan,
                session=session,
                reddit_client=reddit_client,
                crawl_run_id=crawl_run_id,
                community_run_id=community_run_id,
            ),
            deps=deps.build_patrol_deps(),
        )
        return workflow_result.payload

    if plan.plan_kind == "backfill_posts":
        workflow_result = await deps.execute_backfill_posts(
            workflow_input=BackfillPostsPlanWorkflowInput(
                plan=plan,
                session=session,
                reddit_client=reddit_client,
                crawl_run_id=crawl_run_id,
                community_run_id=community_run_id,
            ),
            deps=deps.build_backfill_posts_deps(),
        )
        return workflow_result.payload

    if plan.plan_kind in {
        "seed_top_year",
        "seed_top_all",
        "seed_controversial_year",
    }:
        workflow_result = await deps.execute_seed_archive(
            workflow_input=SeedArchiveWorkflowInput(
                plan=plan,
                session=session,
                reddit_client=reddit_client,
                crawl_run_id=crawl_run_id,
                community_run_id=community_run_id,
            ),
            deps=deps.build_seed_archive_deps(),
        )
        return workflow_result.payload

    if plan.plan_kind == "probe":
        workflow_result = await deps.execute_probe(
            workflow_input=ProbeWorkflowInput(
                plan=plan,
                session=session,
                reddit_client=reddit_client,
                crawl_run_id=crawl_run_id,
                community_run_id=community_run_id,
            ),
            deps=deps.build_probe_deps(),
        )
        return workflow_result.payload

    if plan.plan_kind == "backfill_comments":
        workflow_result = await deps.execute_backfill_comments(
            workflow_input=BackfillCommentsWorkflowInput(
                plan=plan,
                session=session,
                reddit_client=reddit_client,
                crawl_run_id=crawl_run_id,
                community_run_id=community_run_id,
            ),
            deps=deps.build_backfill_comments_deps(),
        )
        return workflow_result.payload

    raise ValueError(f"Unsupported plan_kind: {plan.plan_kind}")


__all__ = [
    "CrawlPlanDispatchDeps",
    "CrawlPlanDispatchInput",
    "dispatch_crawl_plan",
]
