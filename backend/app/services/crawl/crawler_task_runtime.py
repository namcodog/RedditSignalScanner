from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Sequence

import redis.asyncio as redis  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services.community.community_cache_service import upsert_community_cache
from app.services.community.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.crawl.adaptive_scheduler import AdaptiveScheduler
from app.services.crawl.comments_ingest import persist_comments
from app.services.crawl.crawl_plan import CrawlPlanBuilder
from app.services.crawl.crawler_config import TierSettings
from app.services.crawl.patrol_planner_workflow import (
    PatrolPlannerWorkflowDeps,
    PatrolPlannerWorkflowInput,
    run_patrol_planner_workflow,
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
from app.services.crawl.seed_crawl_metrics_service import (
    build_default_seed_crawl_metrics_deps,
    record_seed_crawl_metrics,
)
from app.services.crawl.seed_crawl_runner_workflow import (
    SeedCrawlRunnerWorkflowDeps,
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
from app.services.crawl.target_planner import (
    PatrolTargetPlannerDeps,
    QueuePlannedTargetsDeps,
    plan_patrol_targets,
)
from app.services.infrastructure.cache_manager import DEFAULT_CACHE_TTL_SECONDS, CacheManager
from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.services.infrastructure.subreddit_snapshot import persist_subreddit_snapshot
from app.services.infrastructure.task_outbox_dispatcher import dispatch_pending_task_outbox


def build_planned_target_queue_deps(
    *,
    session_factory: Callable[[], Any],
    enqueue_target_outbox: Callable[..., Awaitable[bool]],
    commit_session: Callable[..., Awaitable[bool]],
) -> QueuePlannedTargetsDeps:
    return QueuePlannedTargetsDeps(
        session_factory=session_factory,
        enqueue_target_outbox=enqueue_target_outbox,
        commit_session=commit_session,
    )


def build_patrol_target_planner_deps(
    *,
    session_factory: Callable[[], Any],
    tier_settings_for: Callable[[CommunityProfile | None], TierSettings | None],
    queue_deps: QueuePlannedTargetsDeps,
    patrol_default_posts_limit: int,
    patrol_max_posts_limit: int,
    effective_batch_size: int,
    effective_time_filter: str,
    effective_sort: str,
    effective_hot_cache_ttl_hours: int,
) -> PatrolTargetPlannerDeps:
    return PatrolTargetPlannerDeps(
        session_factory=session_factory,
        tier_settings_for=tier_settings_for,
        queue_deps=queue_deps,
        patrol_default_posts_limit=patrol_default_posts_limit,
        patrol_max_posts_limit=patrol_max_posts_limit,
        effective_batch_size=effective_batch_size,
        effective_time_filter=effective_time_filter,
        effective_sort=effective_sort,
        effective_hot_cache_ttl_hours=effective_hot_cache_ttl_hours,
    )


def build_planner_workflow_deps(
    *,
    session_factory: Callable[[], Any],
    ensure_crawler_run: Callable[..., Awaitable[Any]],
    commit_session: Callable[..., Awaitable[bool]],
    queue_deps: QueuePlannedTargetsDeps,
    log_swallowed_exception: Callable[[str, Exception], None],
) -> PlannerWorkflowDeps:
    return PlannerWorkflowDeps(
        session_factory=session_factory,
        ensure_crawler_run=ensure_crawler_run,
        commit_session=commit_session,
        queue_deps=queue_deps,
        log_swallowed_exception=log_swallowed_exception,
    )


def build_patrol_planner_workflow_deps(
    *,
    load_seed_profiles: Callable[[bool], Awaitable[tuple[list[CommunityProfile], int]]],
    maybe_trigger_probe_hot_fallback: Callable[[bool], Awaitable[bool]],
    ensure_parent_run: Callable[[str, bool], Awaitable[None]],
    rank_profiles: Callable[[list[CommunityProfile]], Awaitable[list[CommunityProfile]]],
    plan_patrol_targets_func: Callable[[str, list[CommunityProfile], bool], Awaitable[dict[str, Any]]],
    generate_run_id: Callable[[], str],
    log_warning: Callable[..., None],
) -> PatrolPlannerWorkflowDeps:
    return PatrolPlannerWorkflowDeps(
        load_seed_profiles=load_seed_profiles,
        maybe_trigger_probe_hot_fallback=maybe_trigger_probe_hot_fallback,
        ensure_parent_run=ensure_parent_run,
        rank_profiles=rank_profiles,
        plan_patrol_targets=plan_patrol_targets_func,
        generate_run_id=generate_run_id,
        log_warning=log_warning,
    )


def build_seed_crawl_workflow_deps(
    *,
    loader_factory: Callable[..., CommunityPoolLoader],
    plan_builder_factory: Callable[..., CrawlPlanBuilder],
    tier_settings_for: Callable[[CommunityProfile | None], TierSettings | None],
    build_runner_deps: Callable[[], SeedCrawlRunnerWorkflowDeps],
) -> SeedCrawlWorkflowDeps:
    return SeedCrawlWorkflowDeps(
        loader_factory=loader_factory,
        plan_builder_factory=plan_builder_factory,
        tier_settings_for=tier_settings_for,
        run_seed_crawl_with_fallback=run_seed_crawl_with_fallback,
        build_runner_deps=build_runner_deps,
        record_seed_crawl_metrics=record_seed_crawl_metrics,
        build_metrics_deps=build_default_seed_crawl_metrics_deps,
    )


async def build_cache_manager(*, settings: Settings) -> CacheManager:
    return CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )


async def build_reddit_client(
    *,
    settings: Settings,
    module_logger: Any,
) -> RedditAPIClient:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RuntimeError("Reddit API credentials are not configured.")

    limiter = None
    try:
        redis_client = redis.Redis.from_url(settings.reddit_cache_redis_url)
        limiter = GlobalRateLimiter(
            redis_client,
            limit=max(1, int(settings.reddit_rate_limit)),
            window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
            client_id=settings.reddit_client_id or "default",
        )
    except Exception as exc:
        module_logger.warning(
            "Global rate limiter init failed, falling back to local limiter: %s",
            exc,
            exc_info=True,
        )
        limiter = None

    return RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
        max_retries=3,
        retry_backoff_base=5.0,
        global_rate_limiter=limiter,
    )


def build_single_crawl_workflow_deps(
    *,
    cache_manager: CacheManager,
    reddit_client: RedditAPIClient,
    session_factory: Callable[[], Any],
    rollback_with_warning: Callable[[AsyncSession, str], Awaitable[None]],
    log_debug: Callable[[str, Exception], None],
) -> SingleCrawlWorkflowDeps:
    async def _set_cached_posts(
        community_name: str,
        posts: Sequence[RedditPost],
        ttl_seconds: int | None,
    ) -> None:
        await cache_manager.set_cached_posts(
            community_name,
            posts,
            ttl_seconds=ttl_seconds,
        )

    async def _upsert_cache(
        community_name: str,
        posts_cached: int,
        ttl_seconds: int,
    ) -> None:
        await upsert_community_cache(
            community_name,
            posts_cached=posts_cached,
            ttl_seconds=ttl_seconds,
            quality_score=None,
        )

    async def _fetch_comprehensive_posts(
        subreddit: str,
        time_filter: str,
        max_per_strategy: int,
    ) -> Sequence[RedditPost]:
        return await reddit_client.fetch_comprehensive_posts(
            subreddit,
            time_filter=time_filter,
            max_per_strategy=max_per_strategy,
        )

    async def _fetch_subreddit_posts(
        subreddit: str,
        limit: int,
        time_filter: str,
        sort: str,
    ) -> Sequence[RedditPost] | tuple[Sequence[RedditPost], Any]:
        return await reddit_client.fetch_subreddit_posts(
            subreddit,
            limit=limit,
            time_filter=time_filter,
            sort=sort,
        )

    async def _fetch_post_comments(
        post_id: str,
        *,
        sort: str,
        depth: int,
        limit: int,
        mode: str,
    ) -> Sequence[Any]:
        return await reddit_client.fetch_post_comments(
            post_id,
            sort=sort,
            depth=depth,
            limit=limit,
            mode=mode,
        )

    return SingleCrawlWorkflowDeps(
        normalize_subreddit_name=lambda name: (
            str(name).strip()[2:]
            if str(name).strip().lower().startswith("r/")
            else str(name).strip()
        ),
        fetch_comprehensive_posts=_fetch_comprehensive_posts,
        fetch_subreddit_posts=_fetch_subreddit_posts,
        is_rate_limit_error=lambda exc: "rate limit" in str(exc).lower(),
        set_cached_posts=_set_cached_posts,
        upsert_community_cache=_upsert_cache,
        fetch_subreddit_about=reddit_client.fetch_subreddit_about,
        fetch_subreddit_rules=reddit_client.fetch_subreddit_rules,
        session_factory=session_factory,
        persist_subreddit_snapshot=persist_subreddit_snapshot,
        fetch_post_comments=_fetch_post_comments,
        persist_comments=persist_comments,
        rollback_with_warning=rollback_with_warning,
        log_debug=log_debug,
    )


async def run_single_crawl(
    *,
    community_name: str,
    settings: Settings,
    cache_manager: CacheManager,
    reddit_client: RedditAPIClient,
    post_limit: int,
    default_time_filter: str,
    default_sort: str,
    hot_cache_ttl_hours: int | None,
    comments_preview_enabled: bool,
    comments_topn_limit: int,
    build_workflow_deps: Callable[[CacheManager, RedditAPIClient], SingleCrawlWorkflowDeps],
    task_logger: Any,
) -> dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    task_logger.info("开始爬取社区: %s", community_name)
    result = await run_single_crawl_workflow(
        workflow_input=SingleCrawlWorkflowInput(
            community_name=community_name,
            post_limit=post_limit,
            time_filter=default_time_filter,
            sort=default_sort,
            start_time=start_time,
            community_cache_ttl_seconds=(
                settings.reddit_cache_ttl_seconds or DEFAULT_CACHE_TTL_SECONDS
            ),
            hot_cache_ttl_hours=hot_cache_ttl_hours,
            comments_preview_enabled=comments_preview_enabled,
            comments_topn_limit=comments_topn_limit,
        ),
        deps=build_workflow_deps(cache_manager, reddit_client),
    )
    payload = result.payload
    if payload.get("rate_limited"):
        task_logger.warning(
            "[RATE_LIMIT] %s 降采样重试，post_limit: %s -> %s",
            community_name,
            post_limit,
            payload.get("effective_post_limit"),
        )
    task_logger.info(
        "✅ %s: 缓存 %s 个帖子, 耗时 %.2f 秒",
        community_name,
        payload.get("posts_count", 0),
        float(payload.get("duration_seconds", 0.0) or 0.0),
    )
    return payload


async def run_seed_crawl_task(
    *,
    force_refresh: bool,
    settings: Settings,
    build_cache_manager_func: Callable[[Settings], Awaitable[CacheManager]],
    build_reddit_client_func: Callable[[Settings], Awaitable[RedditAPIClient]],
    session_factory: Callable[[], Any],
    effective_batch_size: int,
    effective_max_concurrency: int,
    effective_time_filter: str,
    effective_sort: str,
    build_seed_crawl_workflow_deps_func: Callable[[], SeedCrawlWorkflowDeps],
) -> dict[str, Any]:
    cache_manager = await build_cache_manager_func(settings)
    reddit_client = await build_reddit_client_func(settings)
    async with reddit_client:
        workflow_result = await run_seed_crawl_workflow(
            workflow_input=SeedCrawlWorkflowInput(
                force_refresh=force_refresh,
                settings=settings,
                cache_manager=cache_manager,
                reddit_client=reddit_client,
                session_factory=session_factory,
                effective_batch_size=effective_batch_size,
                effective_max_concurrency=effective_max_concurrency,
                effective_time_filter=effective_time_filter,
                effective_sort=effective_sort,
            ),
            deps=build_seed_crawl_workflow_deps_func(),
        )
        return workflow_result.payload


async def run_patrol_planner_task(
    *,
    force_refresh: bool,
    build_patrol_planner_workflow_deps_func: Callable[[], PatrolPlannerWorkflowDeps],
    task_logger: Any,
    module_logger: Any,
) -> dict[str, Any]:
    result = await run_patrol_planner_workflow(
        PatrolPlannerWorkflowInput(force_refresh=force_refresh),
        deps=build_patrol_planner_workflow_deps_func(),
    )
    if result.status == "idle" and not force_refresh:
        task_logger.info(
            "⏸ 当前没有到期的社区需要抓取（社区总数=%s，全部在冷却中）",
            result.total,
        )
    elif result.run_id:
        module_logger.info("🧾 crawl_run_id=%s (本轮巡航心跳批次号)", result.run_id)
    return result.as_dict()


async def run_backfill_bootstrap_planner(
    *,
    planner_lock: Callable[[str], Any],
    build_planner_workflow_deps_func: Callable[[], PlannerWorkflowDeps],
    backfill_posts_queue: str,
    module_logger: Any,
    workflow_func: Callable[..., Awaitable[Any]],
) -> dict[str, Any]:
    async with planner_lock("planner:backfill_bootstrap") as acquired:
        if not acquired:
            module_logger.warning("backfill bootstrap planner skipped: lock busy")
            return {"status": "locked", "inserted": 0, "enqueued": 0}

        now = datetime.now(timezone.utc)
        max_targets = max(0, int(os.getenv("BACKFILL_BOOTSTRAP_MAX_TARGETS", "20")))
        posts_limit = max(1, int(os.getenv("BACKFILL_BOOTSTRAP_POSTS_LIMIT", "1000")))
        window_days = max(1, int(os.getenv("BACKFILL_BOOTSTRAP_WINDOW_DAYS", "90")))
        cooldown_minutes = max(
            0, int(os.getenv("BACKFILL_BOOTSTRAP_COOLDOWN_MINUTES", "120"))
        )
        error_cooldown_minutes = max(
            0, int(os.getenv("BACKFILL_ERROR_COOLDOWN_MINUTES", "360"))
        )

        if max_targets == 0:
            return {"status": "disabled", "inserted": 0, "enqueued": 0}

        result = await workflow_func(
            BackfillBootstrapPlannerInput(
                now=now,
                max_targets=max_targets,
                posts_limit=posts_limit,
                window_days=window_days,
                cooldown_minutes=cooldown_minutes,
                error_cooldown_minutes=error_cooldown_minutes,
                queue=backfill_posts_queue,
            ),
            deps=build_planner_workflow_deps_func(),
        )
        return result.as_dict()


async def run_seed_sampling_planner(
    *,
    planner_lock: Callable[[str], Any],
    build_planner_workflow_deps_func: Callable[[], PlannerWorkflowDeps],
    backfill_posts_queue: str,
    module_logger: Any,
    workflow_func: Callable[..., Awaitable[Any]],
) -> dict[str, Any]:
    async with planner_lock("planner:seed_sampling") as acquired:
        if not acquired:
            module_logger.warning("seed sampling planner skipped: lock busy")
            return {"status": "locked", "inserted": 0, "enqueued": 0}

        now = datetime.now(timezone.utc)
        cooldown_days = max(1, int(os.getenv("SEED_SAMPLING_COOLDOWN_DAYS", "30")))
        max_targets = max(0, int(os.getenv("SEED_SAMPLING_MAX_TARGETS", "50")))
        posts_limit = max(1, int(os.getenv("SEED_SAMPLING_POSTS_LIMIT", "1000")))
        min_posts = max(0, int(os.getenv("SEED_SAMPLING_MIN_POSTS", str(posts_limit))))

        if max_targets == 0:
            return {"status": "disabled", "inserted": 0, "enqueued": 0}

        result = await workflow_func(
            SeedSamplingPlannerInput(
                now=now,
                cooldown_days=cooldown_days,
                max_targets=max_targets,
                posts_limit=posts_limit,
                min_posts=min_posts,
                queue=backfill_posts_queue,
            ),
            deps=build_planner_workflow_deps_func(),
        )
        return result.as_dict()


async def run_low_quality_communities_planner(
    *,
    build_planner_workflow_deps_func: Callable[[], PlannerWorkflowDeps],
    default_time_filter: str,
    default_sort: str,
    effective_hot_cache_ttl_hours: int,
    task_logger: Any,
    workflow_func: Callable[..., Awaitable[Any]],
) -> dict[str, Any]:
    result = await workflow_func(
        LowQualityPlannerInput(
            now=datetime.now(timezone.utc),
            stale_hours=8,
            max_targets=50,
            posts_limit=100,
            time_filter=default_time_filter,
            sort=default_sort,
            hot_cache_ttl_hours=int(effective_hot_cache_ttl_hours),
        ),
        deps=build_planner_workflow_deps_func(),
    )
    if result.status == "idle":
        task_logger.info("✅ 没有需要补抓的低质量社区")
        return {
            "status": "skipped",
            "mode": "low_quality_patrol_planner",
            "total": 0,
            "inserted": 0,
            "enqueued": 0,
        }
    crawl_run_id = result.run_id or str(uuid.uuid4())
    task_logger.info(
        "✅ 低质量社区补抓下单完成: total=%s, inserted=%s, enqueued=%s",
        result.total or 0,
        result.inserted,
        result.enqueued,
    )
    return {
        "status": "planned",
        "mode": "low_quality_patrol_planner",
        "run_id": crawl_run_id,
        "total": result.total or 0,
        **result.as_dict(),
    }


async def run_task_outbox_dispatch(
    *,
    session_factory: Callable[[], Any],
    send_task: Callable[..., Any],
    execute_task_name: str,
    comments_backfill_queue: str,
    backfill_posts_queue: str,
    commit_session: Callable[..., Awaitable[bool]],
) -> dict[str, Any]:
    batch_size = max(1, int(os.getenv("TASK_OUTBOX_BATCH_SIZE", "50")))
    max_retries = max(1, int(os.getenv("TASK_OUTBOX_MAX_RETRIES", "5")))

    async with session_factory() as session:
        result = await dispatch_pending_task_outbox(
            session,
            batch_size=batch_size,
            max_retries=max_retries,
            send_task=send_task,
            execute_task_name=execute_task_name,
            comments_backfill_queue=comments_backfill_queue,
            backfill_posts_queue=backfill_posts_queue,
        )
        await commit_session(session, context="dispatch_task_outbox")
    return result.as_dict()


async def load_incremental_seed_profiles(
    *,
    session_factory: Callable[[], Any],
    force_refresh: bool,
) -> tuple[list[CommunityProfile], int]:
    async with session_factory() as db:
        loader = CommunityPoolLoader(db)
        if force_refresh:
            await loader.load_seed_communities()
            seeds = await loader.load_community_pool(force_refresh=True)
        else:
            seeds = await loader.get_due_communities()
        total_pool_count = (await loader.get_pool_stats())["total_communities"]
    return seeds, total_pool_count


async def ensure_patrol_parent_run(
    *,
    session_factory: Callable[[], Any],
    ensure_crawler_run: Callable[..., Awaitable[Any]],
    log_swallowed_exception: Callable[[str, Exception], None],
    crawl_run_id: str,
    force_refresh: bool,
) -> None:
    try:
        async with session_factory() as run_session:
            await ensure_crawler_run(
                run_session,
                crawl_run_id=crawl_run_id,
                config={"mode": "patrol_planner", "force_refresh": force_refresh},
            )
            await run_session.commit()
    except Exception as exc:
        log_swallowed_exception(
            "ensure_crawler_run failed in incremental seed planner",
            exc,
        )


async def rank_patrol_seed_profiles(
    *,
    session_factory: Callable[[], Any],
    seed_profiles: list[CommunityProfile],
    module_logger: Any,
) -> list[CommunityProfile]:
    try:
        async with session_factory() as metrics_session:
            scheduler = AdaptiveScheduler(metrics_session, lookback_days=30)
            ordered_names, priority_entries = await scheduler.rank(
                [profile.name for profile in seed_profiles]
            )
            profile_map = {profile.name: profile for profile in seed_profiles}
            ranked = [
                profile_map[name] for name in ordered_names if name in profile_map
            ]
            if priority_entries:
                top_preview = ", ".join(
                    f"{entry.name}({entry.priority_score:.2f},pain={entry.pain_density:.2f})"
                    for entry in priority_entries[:5]
                )
                module_logger.info("📈 自适应排序完成（Top5）：%s", top_preview)
            return ranked
    except Exception:
        module_logger.exception("自适应排序失败，回退原始顺序")
        return seed_profiles


async def plan_patrol_targets_with_parent_run(
    *,
    session_factory: Callable[[], Any],
    ensure_crawler_run: Callable[..., Awaitable[Any]],
    commit_with_warning: Callable[[AsyncSession], Awaitable[bool]],
    log_swallowed_exception: Callable[[str, Exception], None],
    crawl_run_id: str,
    profiles: list[CommunityProfile],
    force_refresh: bool,
    patrol_target_planner_deps: PatrolTargetPlannerDeps,
) -> dict[str, Any]:
    try:
        async with session_factory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={"mode": "patrol_planner", "force_refresh": force_refresh},
            )
            await commit_with_warning(session)
    except Exception as exc:
        log_swallowed_exception("ensure_crawler_run failed in patrol planner", exc)

    result = await plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=force_refresh,
        deps=patrol_target_planner_deps,
    )
    return result.as_dict()


__all__ = [
    "build_cache_manager",
    "build_patrol_planner_workflow_deps",
    "build_patrol_target_planner_deps",
    "build_planned_target_queue_deps",
    "build_planner_workflow_deps",
    "build_reddit_client",
    "build_seed_crawl_workflow_deps",
    "build_single_crawl_workflow_deps",
    "ensure_patrol_parent_run",
    "load_incremental_seed_profiles",
    "plan_patrol_targets_with_parent_run",
    "rank_patrol_seed_profiles",
    "run_backfill_bootstrap_planner",
    "run_low_quality_communities_planner",
    "run_patrol_planner_task",
    "run_seed_crawl_task",
    "run_seed_sampling_planner",
    "run_single_crawl",
    "run_task_outbox_dispatch",
]
