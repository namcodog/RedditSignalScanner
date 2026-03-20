from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Sequence, Tuple, TypeVar, cast

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics
from app.services.infrastructure.cache_manager import CacheManager
from app.services.infrastructure.tiered_scheduler import TieredScheduler
from app.services.crawl.crawler_config import TierSettings, get_crawler_config
from app.services.community.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.crawler_runs_service import complete_crawler_run, ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    fail_crawler_run_target,
)
from app.services.infrastructure.task_outbox_service import (
    enqueue_execute_target_outbox,
)
from app.services.infrastructure.task_outbox_dispatcher import dispatch_pending_task_outbox
from app.utils.asyncio_runner import run as run_coro
from app.services.crawl.crawl_plan import CrawlPlanBuilder
from app.services.crawl.crawler_task_runtime import (
    build_cache_manager as build_cache_manager_runtime,
    build_patrol_planner_workflow_deps as build_patrol_planner_workflow_deps_runtime,
    build_patrol_target_planner_deps as build_patrol_target_planner_deps_runtime,
    build_planned_target_queue_deps as build_planned_target_queue_deps_runtime,
    build_planner_workflow_deps as build_planner_workflow_deps_runtime,
    build_reddit_client as build_reddit_client_runtime,
    build_seed_crawl_workflow_deps as build_seed_crawl_workflow_deps_runtime,
    build_single_crawl_workflow_deps as build_single_crawl_workflow_deps_runtime,
    ensure_patrol_parent_run as ensure_patrol_parent_run_runtime,
    load_incremental_seed_profiles as load_incremental_seed_profiles_runtime,
    plan_patrol_targets_with_parent_run as plan_patrol_targets_with_parent_run_runtime,
    rank_patrol_seed_profiles as rank_patrol_seed_profiles_runtime,
    run_backfill_bootstrap_planner as run_backfill_bootstrap_planner_runtime,
    run_low_quality_communities_planner as run_low_quality_communities_planner_runtime,
    run_patrol_planner_task as run_patrol_planner_task_runtime,
    run_seed_crawl_task as run_seed_crawl_task_runtime,
    run_seed_sampling_planner as run_seed_sampling_planner_runtime,
    run_single_crawl as run_single_crawl_runtime,
    run_task_outbox_dispatch as run_task_outbox_dispatch_runtime,
)
from app.services.crawl.crawler_task_support import (
    commit_with_warning as commit_with_warning_support,
    crawler_run_targets_table_exists as crawler_run_targets_table_exists_support,
    env_int as env_int_support,
    env_truthy as env_truthy_support,
    list_stale_caches as list_stale_caches_support,
    load_last_probe_hot_started_at as load_last_probe_hot_started_at_support,
    log_swallowed_exception as log_swallowed_exception_support,
    mark_empty_hit as mark_empty_hit_support,
    mark_failure_hit as mark_failure_hit_support,
    maybe_trigger_probe_hot_fallback as maybe_trigger_probe_hot_fallback_support,
    planner_lock as planner_lock_support,
    rollback_with_warning as rollback_with_warning_support,
    tier_settings_for as tier_settings_for_support,
)
from app.services.crawl.planner_workflow import (
    BackfillBootstrapPlannerInput,
    LowQualityPlannerInput,
    PlannerWorkflowDeps,
    SeedSamplingPlannerInput,
    plan_backfill_bootstrap_workflow,
    plan_low_quality_communities_workflow,
    plan_seed_sampling_workflow,
)
from app.services.crawl.patrol_planner_workflow import (
    PatrolPlannerWorkflowDeps,
    PatrolPlannerWorkflowInput,
    run_patrol_planner_workflow,
)
from app.services.crawl.target_planner import (
    PatrolTargetPlannerDeps,
    QueuePlannedTargetsDeps,
    build_patrol_target,
    plan_patrol_targets,
    queue_planned_crawl_targets,
)
from app.services.crawl.seed_crawl_metrics_service import (
    SeedCrawlMetricsInput,
    build_default_seed_crawl_metrics_deps,
    record_seed_crawl_metrics,
)
from app.services.crawl.seed_crawl_runner_workflow import (
    SeedCrawlRunnerWorkflowDeps,
    SeedCrawlRunnerWorkflowInput,
    run_seed_crawl_with_fallback,
)
from app.services.crawl.seed_crawl_workflow import (
    SeedCrawlWorkflowDeps,
    SeedCrawlWorkflowInput,
    run_seed_crawl_workflow,
)
from app.services.crawl.single_crawl_workflow import (
    SingleCrawlWorkflowDeps,
    SingleCrawlWorkflowInput,
    run_single_crawl_workflow,
)

T = TypeVar("T")
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditAPIError

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      CRAWLER TASK MODULE STRUCTURE                          ║
# ║                                                                            ║
# ║  Group 1 - Configuration & Utilities:                                      ║
# ║    _tier_settings_for, _chunked, _env_truthy, _env_int,                    ║
# ║    _build_cache_manager, _build_reddit_client, _crawler_run_targets_exists  ║
# ║                                                                            ║
# ║  Group 2 - Locking & Outbox:                                               ║
# ║    _planner_lock, _enqueue_execute_target_outbox,                          ║
# ║    dispatch_task_outbox                                                     ║
# ║                                                                            ║
# ║  Group 3 - Probe Fallback:                                                ║
# ║    _load_last_probe_hot_started_at, _maybe_trigger_probe_hot_fallback      ║
# ║                                                                            ║
# ║  Group 4 - Core Crawl Functions (Celery Tasks):                            ║
# ║    _crawl_single, _crawl_seeds_impl, crawl_community,                     ║
# ║    crawl_seed_communities, crawl_seed_communities_incremental              ║
# ║                                                                            ║
# ║  Group 5 - Quality & Low-Priority Crawl:                                   ║
# ║    crawl_low_quality_communities, _crawl_low_quality_impl,                 ║
# ║    _mark_failure_hit, _mark_empty_hit, list_stale_caches                   ║
# ║                                                                            ║
# ║  Group 6 - Backfill & Sampling Planning:                                   ║
# ║    plan_backfill_bootstrap, _plan_backfill_bootstrap_impl,                 ║
# ║    plan_seed_sampling, _plan_seed_sampling_impl                            ║
# ║                                                                            ║
# ║  Group 7 - Patrol Planning:                                                ║
# ║    _plan_patrol_targets (incremental crawl target generation)              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)

BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")
COMMENTS_BACKFILL_QUEUE = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")

CRAWLER_CONFIG = get_crawler_config()
GLOBAL_SETTINGS = CRAWLER_CONFIG.global_settings

DEFAULT_BATCH_SIZE = int(
    os.getenv("CRAWLER_BATCH_SIZE", str(GLOBAL_SETTINGS.scheduler_batch_size))
)
# 数据库操作：低并发（2）避免 "concurrent operations are not permitted" 错误
# 参考：https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/gather_orm_statements.html
DEFAULT_MAX_CONCURRENCY = int(
    os.getenv("CRAWLER_MAX_CONCURRENCY", str(GLOBAL_SETTINGS.max_db_concurrency))
)
DEFAULT_POST_LIMIT = int(os.getenv("CRAWLER_POST_LIMIT", "100"))
DEFAULT_TIME_FILTER = os.getenv("CRAWLER_TIME_FILTER", "month")
DEFAULT_SORT = os.getenv("CRAWLER_SORT", "top")

EFFECTIVE_BATCH_SIZE = DEFAULT_BATCH_SIZE
EFFECTIVE_MAX_CONCURRENCY = DEFAULT_MAX_CONCURRENCY
EFFECTIVE_TIME_FILTER = DEFAULT_TIME_FILTER
EFFECTIVE_SORT = DEFAULT_SORT
EFFECTIVE_HOT_CACHE_TTL_HOURS = GLOBAL_SETTINGS.hot_cache_ttl_hours

if CRAWLER_CONFIG.tiers:
    primary_tier = CRAWLER_CONFIG.tiers[0]
    if "CRAWLER_POST_LIMIT" not in os.environ:
        DEFAULT_POST_LIMIT = primary_tier.post_limit
    if "CRAWLER_TIME_FILTER" not in os.environ:
        EFFECTIVE_TIME_FILTER = primary_tier.time_filter
    if "CRAWLER_SORT" not in os.environ:
        EFFECTIVE_SORT = primary_tier.pick_sort(default_sort=EFFECTIVE_SORT)


# ── Group 1: Configuration & Utilities ─────────────────────────────────────


def _log_swallowed_exception(context: str, exc: Exception) -> None:
    log_swallowed_exception_support(_MODULE_LOGGER, context, exc)


async def _rollback_with_warning(session: AsyncSession, *, context: str) -> None:
    await rollback_with_warning_support(
        session,
        context=context,
        log_swallowed_exception_func=_log_swallowed_exception,
    )


async def _commit_with_warning(session: AsyncSession, *, context: str) -> bool:
    return await commit_with_warning_support(
        session,
        context=context,
        rollback_with_warning_func=lambda s: _rollback_with_warning(s, context=context),
        log_swallowed_exception_func=_log_swallowed_exception,
    )


def _tier_settings_for(profile: CommunityProfile | None) -> TierSettings | None:
    return tier_settings_for_support(profile, crawler_config=CRAWLER_CONFIG)


def _chunked(
    items: Sequence[T], size: int
) -> Iterable[Sequence[T]]:
    if size <= 0:
        size = len(items) or 1
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _env_truthy(name: str, default: str = "0") -> bool:
    return env_truthy_support(name, default)


def _env_int(name: str, default: int) -> int:
    return env_int_support(name, default)


async def _crawler_run_targets_table_exists(session: AsyncSession) -> bool:
    return await crawler_run_targets_table_exists_support(session)


def _planned_target_queue_deps() -> QueuePlannedTargetsDeps:
    return build_planned_target_queue_deps_runtime(
        session_factory=SessionFactory,
        enqueue_target_outbox=_enqueue_execute_target_outbox,
        commit_session=lambda session, context=None: _commit_with_warning(
            session,
            context=context or "queue_planned_targets",
        ),
    )


def _patrol_target_planner_deps() -> PatrolTargetPlannerDeps:
    return build_patrol_target_planner_deps_runtime(
        session_factory=SessionFactory,
        tier_settings_for=_tier_settings_for,
        queue_deps=_planned_target_queue_deps(),
        patrol_default_posts_limit=int(os.getenv("PATROL_POST_LIMIT", "80")),
        patrol_max_posts_limit=int(os.getenv("PATROL_MAX_POST_LIMIT", "100")),
        effective_batch_size=EFFECTIVE_BATCH_SIZE,
        effective_time_filter=EFFECTIVE_TIME_FILTER,
        effective_sort=EFFECTIVE_SORT,
        effective_hot_cache_ttl_hours=EFFECTIVE_HOT_CACHE_TTL_HOURS,
    )


def _planner_workflow_deps() -> PlannerWorkflowDeps:
    return build_planner_workflow_deps_runtime(
        session_factory=SessionFactory,
        ensure_crawler_run=ensure_crawler_run,
        commit_session=lambda session, context=None: _commit_with_warning(
            session,
            context=context or "planner_workflow",
        ),
        queue_deps=_planned_target_queue_deps(),
        log_swallowed_exception=_log_swallowed_exception,
    )


def _patrol_planner_workflow_deps() -> PatrolPlannerWorkflowDeps:
    return build_patrol_planner_workflow_deps_runtime(
        load_seed_profiles=_load_incremental_seed_profiles,
        maybe_trigger_probe_hot_fallback=_maybe_trigger_probe_hot_fallback,
        ensure_parent_run=_ensure_patrol_parent_run,
        rank_profiles=_rank_patrol_seed_profiles,
        plan_patrol_targets_func=_plan_patrol_targets_workflow,
        generate_run_id=lambda: str(uuid.uuid4()),
        log_warning=logger.warning,
    )


def _seed_crawl_workflow_deps() -> SeedCrawlWorkflowDeps:
    return build_seed_crawl_workflow_deps_runtime(
        loader_factory=CommunityPoolLoader,
        plan_builder_factory=CrawlPlanBuilder,
        tier_settings_for=_tier_settings_for,
        build_runner_deps=lambda: SeedCrawlRunnerWorkflowDeps(
            crawl_single=_crawl_single,
            log_swallowed_exception=_log_swallowed_exception,
        ),
    )


# ── Group 2: Locking & Outbox ──────────────────────────────────────────────


@asynccontextmanager
async def _planner_lock(lock_key: str) -> Iterable[bool]:
    async with planner_lock_support(
        session_factory=SessionFactory,
        lock_key=lock_key,
        log_swallowed_exception_func=_log_swallowed_exception,
    ) as acquired:
        yield acquired


async def _enqueue_execute_target_outbox(
    *,
    session: AsyncSession,
    target_id: str,
    queue: str,
    countdown: int | None = None,
) -> bool:
    return await enqueue_execute_target_outbox(
        session,
        target_id=target_id,
        queue=queue,
        countdown=countdown,
    )


# ── Group 3: Probe Fallback ────────────────────────────────────────────────


async def _load_last_probe_hot_started_at(session: AsyncSession) -> datetime | None:
    return await load_last_probe_hot_started_at_support(session)


async def _maybe_trigger_probe_hot_fallback(
    *, due_count: int, total_pool_count: int
) -> bool:
    return await maybe_trigger_probe_hot_fallback_support(
        due_count=due_count,
        total_pool_count=total_pool_count,
        session_factory=SessionFactory,
        crawler_run_targets_table_exists_func=_crawler_run_targets_table_exists,
        load_last_probe_hot_started_at_func=_load_last_probe_hot_started_at,
        env_truthy_func=_env_truthy,
        env_int_func=_env_int,
        send_task=celery_app.send_task,
        module_logger=_MODULE_LOGGER,
    )


async def _build_cache_manager(settings: Settings) -> CacheManager:
    return await build_cache_manager_runtime(settings=settings)


async def _build_reddit_client(settings: Settings) -> RedditAPIClient:
    return await build_reddit_client_runtime(
        settings=settings,
        module_logger=_MODULE_LOGGER,
    )


# ── Group 4: Core Crawl Functions ──────────────────────────────────────────


async def _crawl_single(
    community_name: str,
    *,
    settings: Settings,
    cache_manager: CacheManager,
    reddit_client: RedditAPIClient,
    post_limit: int,
    time_filter: str | None = None,
    sort: str | None = None,
    hot_cache_ttl_hours: int | None = None,
    tier_name: str | None = None,
) -> dict[str, Any]:
    return await run_single_crawl_runtime(
        community_name=community_name,
        settings=settings,
        cache_manager=cache_manager,
        reddit_client=reddit_client,
        post_limit=post_limit,
        default_time_filter=time_filter or EFFECTIVE_TIME_FILTER,
        default_sort=sort or EFFECTIVE_SORT,
        hot_cache_ttl_hours=hot_cache_ttl_hours,
        comments_preview_enabled=settings.incremental_comments_preview_enabled,
        comments_topn_limit=getattr(settings, "comments_topn_limit", 20),
        build_workflow_deps=lambda cm, rc: _single_crawl_workflow_deps(
            cache_manager=cm,
            reddit_client=rc,
        ),
        task_logger=logger,
    )


def _single_crawl_workflow_deps(
    *,
    cache_manager: CacheManager,
    reddit_client: RedditAPIClient,
) -> SingleCrawlWorkflowDeps:
    return build_single_crawl_workflow_deps_runtime(
        cache_manager=cache_manager,
        reddit_client=reddit_client,
        session_factory=SessionFactory,
        rollback_with_warning=lambda session, context: _rollback_with_warning(
            session,
            context=context,
        ),
        log_debug=lambda context, exc: _MODULE_LOGGER.debug("%s: %s", context, exc),
    )


async def _crawl_seeds_impl(force_refresh: bool = False) -> dict[str, Any]:
    """旧版抓取：只写 Redis 缓存（保留用于兼容）"""
    settings = get_settings()
    return await run_seed_crawl_task_runtime(
        force_refresh=force_refresh,
        settings=settings,
        build_cache_manager_func=_build_cache_manager,
        build_reddit_client_func=_build_reddit_client,
        session_factory=SessionFactory,
        effective_batch_size=EFFECTIVE_BATCH_SIZE,
        effective_max_concurrency=EFFECTIVE_MAX_CONCURRENCY,
        effective_time_filter=EFFECTIVE_TIME_FILTER,
        effective_sort=EFFECTIVE_SORT,
        build_seed_crawl_workflow_deps_func=_seed_crawl_workflow_deps,
    )


# ── Group 5: Quality & Failure Tracking ────────────────────────────────────


async def _mark_failure_hit(community_name: str) -> None:
    await mark_failure_hit_support(
        session_factory=SessionFactory,
        community_name=community_name,
    )


async def _plan_patrol_targets(
    *,
    crawl_run_id: str,
    profiles: list[CommunityProfile],
    force_refresh: bool,
) -> dict[str, Any]:
    return await plan_patrol_targets_with_parent_run_runtime(
        session_factory=SessionFactory,
        ensure_crawler_run=ensure_crawler_run,
        commit_with_warning=lambda session: _commit_with_warning(
            session,
            context="plan_patrol_targets ensure_run",
        ),
        log_swallowed_exception=_log_swallowed_exception,
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=force_refresh,
        patrol_target_planner_deps=_patrol_target_planner_deps(),
    )


async def _load_incremental_seed_profiles(
    force_refresh: bool,
) -> tuple[list[CommunityProfile], int]:
    seeds, total_pool_count = await load_incremental_seed_profiles_runtime(
        session_factory=SessionFactory,
        force_refresh=force_refresh,
    )
    if force_refresh:
        _MODULE_LOGGER.info("🔄 强制刷新模式：下单全量 %s 个社区", len(seeds))
    return seeds, total_pool_count


async def _ensure_patrol_parent_run(crawl_run_id: str, force_refresh: bool) -> None:
    await ensure_patrol_parent_run_runtime(
        session_factory=SessionFactory,
        ensure_crawler_run=ensure_crawler_run,
        log_swallowed_exception=_log_swallowed_exception,
        crawl_run_id=crawl_run_id,
        force_refresh=force_refresh,
    )


async def _rank_patrol_seed_profiles(
    seed_profiles: list[CommunityProfile],
) -> list[CommunityProfile]:
    return await rank_patrol_seed_profiles_runtime(
        session_factory=SessionFactory,
        seed_profiles=seed_profiles,
        module_logger=_MODULE_LOGGER,
    )


async def _plan_patrol_targets_workflow(
    crawl_run_id: str,
    profiles: list[CommunityProfile],
    force_refresh: bool,
) -> dict[str, Any]:
    return await _plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=force_refresh,
    )


async def _plan_backfill_bootstrap_impl() -> dict[str, Any]:
    """Backfill bootstrap planner (status-driven)."""
    return await run_backfill_bootstrap_planner_runtime(
        planner_lock=_planner_lock,
        build_planner_workflow_deps_func=_planner_workflow_deps,
        backfill_posts_queue=BACKFILL_POSTS_QUEUE,
        module_logger=_MODULE_LOGGER,
        workflow_func=plan_backfill_bootstrap_workflow,
    )


async def _plan_seed_sampling_impl() -> dict[str, Any]:
    """Seed sampling planner for DONE_CAPPED communities."""
    return await run_seed_sampling_planner_runtime(
        planner_lock=_planner_lock,
        build_planner_workflow_deps_func=_planner_workflow_deps,
        backfill_posts_queue=BACKFILL_POSTS_QUEUE,
        module_logger=_MODULE_LOGGER,
        workflow_func=plan_seed_sampling_workflow,
    )


async def _dispatch_task_outbox_impl() -> dict[str, Any]:
    return await run_task_outbox_dispatch_runtime(
        session_factory=SessionFactory,
        send_task=celery_app.send_task,
        execute_task_name="tasks.crawler.execute_target",
        comments_backfill_queue=COMMENTS_BACKFILL_QUEUE,
        backfill_posts_queue=BACKFILL_POSTS_QUEUE,
        commit_session=lambda session, context=None: _commit_with_warning(
            session,
            context=context or "dispatch_task_outbox",
        ),
    )


@celery_app.task(name="tasks.crawler.dispatch_task_outbox")  # type: ignore[misc]
def dispatch_task_outbox() -> dict[str, Any]:
    """Dispatch pending crawler outbox events."""
    try:
        return run_coro(_dispatch_task_outbox_impl())
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ task_outbox 派发失败")
        raise


async def _crawl_seeds_incremental_impl(force_refresh: bool = False) -> dict[str, Any]:
    """增量巡航心跳（planner-only）：只生成计划并派发 execute_target。"""
    return await run_patrol_planner_task_runtime(
        force_refresh=force_refresh,
        build_patrol_planner_workflow_deps_func=_patrol_planner_workflow_deps,
        task_logger=logger,
        module_logger=_MODULE_LOGGER,
    )


async def _crawl_single_impl(community_name: str, tier_name: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    cache_manager = await _build_cache_manager(settings)
    reddit_client = await _build_reddit_client(settings)
    async with reddit_client:
        return await _crawl_single(
            community_name,
            settings=settings,
            cache_manager=cache_manager,
            reddit_client=reddit_client,
            post_limit=DEFAULT_POST_LIMIT,
            tier_name=tier_name,
        )


@celery_app.task(name="tasks.crawler.crawl_community", bind=True, max_retries=3)  # type: ignore[misc]
def crawl_community(self: Any, community_name: str) -> dict[str, Any]:
    if not community_name:
        raise ValueError("community_name is required")
    try:
        return run_coro(_crawl_single_impl(community_name))
    except RedditAPIError as exc:
        logger.error("❌ %s: Reddit API 错误 - %s", community_name, exc)
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:  # pragma: no cover - Celery will capture traceback
        logger.exception("❌ %s: 未预期的错误", community_name)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.crawler.crawl_seed_communities")  # type: ignore[misc]
def crawl_seed_communities(force_refresh: bool = False) -> dict[str, Any]:
    """旧版抓取任务（只写 Redis 缓存）"""
    try:
        return run_coro(_crawl_seeds_impl(force_refresh=force_refresh))
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 种子社区批量爬取失败")
        raise


@celery_app.task(name="tasks.crawler.crawl_seed_communities_incremental")  # type: ignore[misc]
def crawl_seed_communities_incremental(force_refresh: bool = False) -> dict[str, Any]:
    """新版增量抓取任务（冷热双写 + 水位线）"""
    try:
        return run_coro(_crawl_seeds_incremental_impl(force_refresh=force_refresh))
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 增量抓取失败")
        raise


async def _crawl_low_quality_communities_impl() -> dict[str, Any]:
    """精准补抓低质量社区（planner-only）。

    说明：
    - 只负责下单 queued targets，并 enqueue execute_target
    - 真正抓取/落库/水位线结账统一走 execute_target
    """
    return await run_low_quality_communities_planner_runtime(
        build_planner_workflow_deps_func=_planner_workflow_deps,
        default_time_filter=DEFAULT_TIME_FILTER,
        default_sort=DEFAULT_SORT,
        effective_hot_cache_ttl_hours=int(EFFECTIVE_HOT_CACHE_TTL_HOURS),
        task_logger=logger,
        workflow_func=plan_low_quality_communities_workflow,
    )


async def _mark_empty_hit(community_name: str) -> None:
    await mark_empty_hit_support(
        session_factory=SessionFactory,
        community_name=community_name,
    )


async def list_stale_caches(threshold_minutes: int = 90) -> List[Tuple[str, datetime]]:
    return await list_stale_caches_support(
        session_factory=SessionFactory,
        threshold_minutes=threshold_minutes,
    )


@celery_app.task(name="tasks.crawler.crawl_low_quality_communities")  # type: ignore[misc]
def crawl_low_quality_communities() -> dict[str, Any]:
    """精准补抓低质量社区任务（T1.8）"""
    try:
        return run_coro(_crawl_low_quality_communities_impl())
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 低质量社区补抓失败")
        raise


@celery_app.task(name="tasks.crawler.plan_backfill_bootstrap")  # type: ignore[misc]
def plan_backfill_bootstrap() -> dict[str, Any]:
    """Planner: enqueue backfill bootstrap targets by status."""
    try:
        return run_coro(_plan_backfill_bootstrap_impl())
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 回填 bootstrap 规划失败")
        raise


@celery_app.task(name="tasks.crawler.plan_seed_sampling")  # type: ignore[misc]
def plan_seed_sampling() -> dict[str, Any]:
    """Planner: enqueue seed sampling targets for DONE_CAPPED."""
    try:
        return run_coro(_plan_seed_sampling_impl())
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ Seed 采样规划失败")
        raise


__all__ = [
    "crawl_community",
    "crawl_seed_communities",
    "crawl_seed_communities_incremental",
    "crawl_low_quality_communities",
    "list_stale_caches",
]
