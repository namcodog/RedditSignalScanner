from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.backfill_comments_workflow import (
    count_existing_backfill_comments,
    execute_backfill_comments_workflow,
    resolve_backfill_post_context,
)
from app.services.crawl.backfill_posts_plan_workflow import (
    execute_backfill_posts_plan_workflow,
)
from app.services.crawl.comments_ingest import persist_comments
from app.services.crawl.crawl_plan_dispatcher import (
    CrawlPlanDispatchInput,
    dispatch_crawl_plan,
)
from app.services.crawl.execute_plan_deps_factory import (
    ExecuteCrawlPlanDepsFactoryInput,
    build_execute_crawl_plan_dispatch_deps,
)
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.crawl.probe_workflow import execute_probe_workflow
from app.services.crawl.patrol_workflow import execute_patrol_workflow
from app.services.crawl.seed_archive_workflow import execute_seed_archive_workflow
from app.services.labeling.labeling_service import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.infrastructure.reddit_client import RedditAPIClient


async def execute_crawl_plan(
    *,
    plan: CrawlPlanContract,
    session: AsyncSession,
    reddit_client: RedditAPIClient,
    crawl_run_id: str,
    community_run_id: str,
) -> dict[str, object]:
    """
    统一执行器（v1）：给定一张 CrawlPlan 合同，执行并返回结果。

    说明：
    - 这是“收口”的关键：巡航/补数最终都走同一段执行逻辑。
    - 语义/探针/评论回填会在后续逐步接进来。
    """
    return await dispatch_crawl_plan(
        CrawlPlanDispatchInput(
            plan=plan,
            session=session,
            reddit_client=reddit_client,
            crawl_run_id=crawl_run_id,
            community_run_id=community_run_id,
        ),
        build_execute_crawl_plan_dispatch_deps(
            ExecuteCrawlPlanDepsFactoryInput(
                execute_patrol=execute_patrol_workflow,
                execute_backfill_posts=execute_backfill_posts_plan_workflow,
                execute_seed_archive=execute_seed_archive_workflow,
                execute_probe=execute_probe_workflow,
                execute_backfill_comments=execute_backfill_comments_workflow,
                crawler_factory=IncrementalCrawler,
                resolve_post_context=resolve_backfill_post_context,
                count_existing_comments=count_existing_backfill_comments,
                persist_comments=persist_comments,
                classify_comments=classify_and_label_comments,
                extract_comment_entities=extract_and_label_entities_for_comments,
            ),
        ),
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["execute_crawl_plan", "utc_now_iso"]
