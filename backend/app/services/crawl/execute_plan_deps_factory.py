from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.services.crawl.backfill_comments_workflow import BackfillCommentsWorkflowDeps
from app.services.crawl.backfill_posts_plan_workflow import BackfillPostsPlanWorkflowDeps
from app.services.crawl.crawl_plan_dispatcher import CrawlPlanDispatchDeps
from app.services.crawl.patrol_workflow import PatrolWorkflowDeps
from app.services.crawl.probe_workflow import ProbeWorkflowDeps
from app.services.crawl.seed_archive_workflow import SeedArchiveWorkflowDeps


@dataclass(slots=True)
class ExecuteCrawlPlanDepsFactoryInput:
    execute_patrol: Callable[..., Awaitable[Any]]
    execute_backfill_posts: Callable[..., Awaitable[Any]]
    execute_seed_archive: Callable[..., Awaitable[Any]]
    execute_probe: Callable[..., Awaitable[Any]]
    execute_backfill_comments: Callable[..., Awaitable[Any]]
    crawler_factory: type[Any]
    resolve_post_context: Callable[..., Awaitable[Any]]
    count_existing_comments: Callable[..., Awaitable[int]]
    persist_comments: Callable[..., Awaitable[Any]]
    classify_comments: Callable[..., Awaitable[Any]]
    extract_comment_entities: Callable[..., Awaitable[Any]]


def build_execute_crawl_plan_dispatch_deps(
    factory_input: ExecuteCrawlPlanDepsFactoryInput,
) -> CrawlPlanDispatchDeps:
    return CrawlPlanDispatchDeps(
        execute_patrol=factory_input.execute_patrol,
        execute_backfill_posts=factory_input.execute_backfill_posts,
        execute_seed_archive=factory_input.execute_seed_archive,
        execute_probe=factory_input.execute_probe,
        execute_backfill_comments=factory_input.execute_backfill_comments,
        build_patrol_deps=lambda: PatrolWorkflowDeps(
            crawler_factory=factory_input.crawler_factory,
        ),
        build_backfill_posts_deps=lambda: BackfillPostsPlanWorkflowDeps(
            crawler_factory=factory_input.crawler_factory,
        ),
        build_seed_archive_deps=lambda: SeedArchiveWorkflowDeps(
            crawler_factory=factory_input.crawler_factory,
        ),
        build_probe_deps=lambda: ProbeWorkflowDeps(),
        build_backfill_comments_deps=lambda: BackfillCommentsWorkflowDeps(
            resolve_post_context=factory_input.resolve_post_context,
            count_existing_comments=factory_input.count_existing_comments,
            persist_comments=factory_input.persist_comments,
            classify_comments=factory_input.classify_comments,
            extract_comment_entities=factory_input.extract_comment_entities,
        ),
    )


__all__ = [
    "ExecuteCrawlPlanDepsFactoryInput",
    "build_execute_crawl_plan_dispatch_deps",
]
