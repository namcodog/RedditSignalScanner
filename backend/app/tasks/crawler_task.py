from __future__ import annotations

import logging
import os
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Sequence, Tuple, TypeVar, cast

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.crawl_metrics import CrawlMetrics
from app.services.infrastructure.cache_manager import DEFAULT_CACHE_TTL_SECONDS, CacheManager
from app.services.crawl.crawler_config import TierSettings, get_crawler_config
from app.services.community.community_cache_service import upsert_community_cache
from app.services.community.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.crawler_runs_service import complete_crawler_run, ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    ensure_crawler_run_target,
    fail_crawler_run_target,
)
from app.services.infrastructure.task_outbox_service import (
    enqueue_execute_target_outbox,
    fetch_pending_task_outbox,
    mark_task_outbox_failed,
    mark_task_outbox_sent,
    resolve_outbox_env_fingerprint,
)
from app.utils.asyncio_runner import run as run_coro
from app.services.crawl.crawl_plan import CrawlPlanBuilder
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.utils.subreddit import subreddit_key

T = TypeVar("T")
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditAPIError, RedditPost
from app.services.crawl.adaptive_scheduler import AdaptiveScheduler
from app.services.crawl.comments_ingest import persist_comments
from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore
from app.services.infrastructure.tiered_scheduler import TieredScheduler
from app.services.infrastructure.subreddit_snapshot import persist_subreddit_snapshot

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


def _tier_settings_for(profile: CommunityProfile | None) -> TierSettings | None:
    if profile is None:
        return None
    return CRAWLER_CONFIG.resolve_tier(profile.tier)


def _chunked(
    items: Sequence[T], size: int
) -> Iterable[Sequence[T]]:
    if size <= 0:
        size = len(items) or 1
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


async def _crawler_run_targets_table_exists(session: AsyncSession) -> bool:
    exists = (
        await session.execute(text("SELECT to_regclass('public.crawler_run_targets')"))
    ).scalar_one_or_none()
    return bool(exists)


@asynccontextmanager
async def _planner_lock(lock_key: str) -> Iterable[bool]:
    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        acquired = False
        try:
            result = await session.execute(
                text("SELECT pg_try_advisory_lock(hashtext(:key))"),
                {"key": lock_key},
            )
            acquired = bool(result.scalar_one_or_none())
        except Exception:
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    await session.execute(
                        text("SELECT pg_advisory_unlock(hashtext(:key))"),
                        {"key": lock_key},
                    )
                except Exception:
                    pass


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


def _normalize_outbox_payload(raw_payload: Any) -> dict[str, Any]:
    if raw_payload is None:
        return {}
    if isinstance(raw_payload, dict):
        return raw_payload
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def _load_last_probe_hot_started_at(session: AsyncSession) -> datetime | None:
    result = await session.execute(
        text(
            """
            SELECT MAX(started_at) AS last_started
            FROM crawler_run_targets
            WHERE (config->>'plan_kind') = 'probe'
              AND (config->'meta'->>'source') = 'hot'
            """
        )
    )
    return result.scalar_one_or_none()


async def _maybe_trigger_probe_hot_fallback(
    *, due_count: int, total_pool_count: int
) -> bool:
    if not _env_truthy("PROBE_HOT_FALLBACK_ENABLED", "1"):
        return False

    min_due = max(0, _env_int("PROBE_HOT_FALLBACK_MIN_DUE", 3))
    if due_count >= min_due:
        return False

    cooldown_minutes = max(0, _env_int("PROBE_HOT_FALLBACK_COOLDOWN_MINUTES", 720))
    posts_per_source = max(5, _env_int("PROBE_HOT_FALLBACK_POSTS_PER_SOURCE", 15))

    async with SessionFactory() as session:
        if not await _crawler_run_targets_table_exists(session):
            _MODULE_LOGGER.info(
                "probe hot fallback skipped: crawler_run_targets missing"
            )
            return False
        last_started = await _load_last_probe_hot_started_at(session)

    if last_started is not None:
        if last_started.tzinfo is None:
            last_started = last_started.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_started
        if delta < timedelta(minutes=cooldown_minutes):
            _MODULE_LOGGER.info(
                "probe hot fallback skipped: cooldown (last=%s, cooldown=%smin)",
                last_started.isoformat(),
                cooldown_minutes,
            )
            return False

    _MODULE_LOGGER.info(
        "probe hot fallback triggered: due=%s total_pool=%s",
        due_count,
        total_pool_count,
    )
    try:
        celery_app.send_task(
            "tasks.probe.run_hot_probe",
            kwargs={
                "reason": "patrol_idle_fallback",
                "posts_per_source": posts_per_source,
            },
            queue="probe_queue",
        )
    except Exception:
        _MODULE_LOGGER.exception("probe hot fallback dispatch failed")
        return False

    return True


async def _build_cache_manager(settings: Settings) -> CacheManager:
    return CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )


async def _build_reddit_client(settings: Settings) -> RedditAPIClient:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RuntimeError("Reddit API credentials are not configured.")

    # 构建全局限流器（跨 Worker），如失败则回退为 None
    limiter = None
    try:
        rclient = redis.Redis.from_url(settings.reddit_cache_redis_url)
        limiter = GlobalRateLimiter(
            rclient,
            limit=max(1, int(settings.reddit_rate_limit)),
            window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
            client_id=settings.reddit_client_id or "default",
        )
    except Exception as e:
        _MODULE_LOGGER.warning(
            "Global rate limiter init failed, falling back to local limiter: %s",
            e,
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
        max_retries=3,  # 429 错误最大重试 3 次
        retry_backoff_base=5.0,  # 指数退避基础等待时间 5 秒
        global_rate_limiter=limiter,
    )


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
    start_time = datetime.now(timezone.utc)
    logger.info("开始爬取社区: %s", community_name)

    # Reddit API 期望的不带前缀名称，例如 'Entrepreneur' 而不是 'r/Entrepreneur'
    raw_name = str(community_name).strip()
    api_subreddit = raw_name[2:] if raw_name.lower().startswith("r/") else raw_name

    rate_limited = False
    effective_post_limit = post_limit

    # 🔥 使用多策略抓取（top + new + hot），获取最大覆盖率
    # 每种策略最多1000个帖子，去重后平均~1,242个帖子/社区
    try:
        if post_limit > 100:
            posts = await reddit_client.fetch_comprehensive_posts(
                api_subreddit,
                time_filter=(time_filter or EFFECTIVE_TIME_FILTER),
                max_per_strategy=post_limit,
            )
        else:
            # 小批量抓取：使用单一策略
            posts_tuple = await reddit_client.fetch_subreddit_posts(
                api_subreddit,
                limit=post_limit,
                time_filter=(time_filter or EFFECTIVE_TIME_FILTER),
                sort=(sort or EFFECTIVE_SORT),
            )
            posts = posts_tuple[0] if isinstance(posts_tuple, tuple) else posts_tuple
    except RedditAPIError as exc:
        # 若命中速率限制，主动降采样再试一次，避免整个批次失败
        if "rate limit" in str(exc).lower():
            rate_limited = True
            effective_post_limit = min(80, max(20, int(post_limit / 2) or 20))
            logger.warning(
                "[RATE_LIMIT] %s 降采样重试，post_limit: %s -> %s",
                community_name,
                post_limit,
                effective_post_limit,
            )
            posts_tuple = await reddit_client.fetch_subreddit_posts(
                api_subreddit,
                limit=effective_post_limit,
                time_filter=(time_filter or EFFECTIVE_TIME_FILTER),
                sort=(sort or EFFECTIVE_SORT),
            )
            posts = posts_tuple[0] if isinstance(posts_tuple, tuple) else posts_tuple
        else:
            raise

    # 内部缓存与数据库仍然使用带前缀的社区名，保证与社区池/键命名一致
    ttl_seconds = None
    if hot_cache_ttl_hours is not None:
        ttl_seconds = max(60, int(hot_cache_ttl_hours) * 3600)
    await cache_manager.set_cached_posts(community_name, posts, ttl_seconds=ttl_seconds)
    await upsert_community_cache(
        community_name,
        posts_cached=len(posts),
        ttl_seconds=settings.reddit_cache_ttl_seconds or DEFAULT_CACHE_TTL_SECONDS,
        quality_score=None,
    )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("✅ %s: 缓存 %s 个帖子, 耗时 %.2f 秒", community_name, len(posts), duration)

    # 记录 subreddit 快照（订阅数/活跃数/规则文本）
    try:
        about = await reddit_client.fetch_subreddit_about(api_subreddit)
        rules_text = await reddit_client.fetch_subreddit_rules(api_subreddit)
        async with SessionFactory() as db:
            await persist_subreddit_snapshot(
                db,
                subreddit=api_subreddit,
                subscribers=about.get("subscribers"),
                active_user_count=about.get("active_user_count"),
                rules_text=rules_text,
                over18=about.get("over18"),
            )
            await db.commit()
    except Exception as exc:
        _MODULE_LOGGER.debug("subreddit snapshot failed for %s: %s", api_subreddit, exc)

    # 可选：为抓取到的帖子同步评论（不阻断主流程）
    # 🔥 根据社区tier配置评论抓取策略：高价值社区抓取全量评论
    if settings.incremental_comments_preview_enabled and posts:
        try:
            # 增量轨：只抓预览评论（Top-N），不抓全量评论树
            comment_depth = 1
            comment_limit = min(getattr(settings, "comments_topn_limit", 20), 20)
            comment_mode = "topn"

            comment_crawl_run_id = str(uuid.uuid4())
            _MODULE_LOGGER.info(
                "🧾 comment_crawl_run_id=%s (%s 预览评论同步批次号)",
                comment_crawl_run_id,
                community_name,
            )
            async with SessionFactory() as db:
                for p in posts:
                    try:
                        items = await reddit_client.fetch_post_comments(
                            p.id,
                            sort="confidence",
                            depth=comment_depth,
                            limit=comment_limit,
                            mode=comment_mode,
                        )
                        if not items:
                            continue
                        await persist_comments(
                            db,
                            source_post_id=p.id,
                            subreddit=api_subreddit,
                            comments=items,
                            source_track="incremental_preview",
                            crawl_run_id=comment_crawl_run_id,
                        )
                        # 每个帖子独立提交，避免长事务持锁导致后续帖子阻塞
                        await db.commit()
                    except Exception as exc:
                        # 出现错误时立即回滚，防止连接停留在 aborted 状态
                        try:
                            await db.rollback()
                        except Exception:
                            pass
                        _MODULE_LOGGER.debug("Comment sync failed for %s: %s", p.id, exc)
        except Exception as exc:
            _MODULE_LOGGER.debug("Comment sync skipped: %s", exc)

    return {
        "community": community_name,
        "posts_count": len(posts),
        "status": "success",
        "duration_seconds": duration,
        "rate_limited": rate_limited,
        "effective_post_limit": effective_post_limit,
    }


async def _crawl_seeds_impl(force_refresh: bool = False) -> dict[str, Any]:
    """旧版抓取：只写 Redis 缓存（保留用于兼容）"""
    settings = get_settings()
    cache_manager = await _build_cache_manager(settings)
    reddit_client = await _build_reddit_client(settings)

    async with reddit_client:
        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            plan_builder = CrawlPlanBuilder(db)
            if force_refresh:
                await loader.load_seed_communities()

            plan = await plan_builder.build_plan()
            seeds = [
                entry.profile
                for entry in plan
                if entry.status == "active" and entry.crawl_track != "none"
            ]
        # 爬取所有活跃社区（high, medium, low 优先级）
        # 兼容多种 tier 命名（gold/silver/seed → high/medium/low）
        allowed_tiers = {"high", "medium", "low", "gold", "silver", "seed"}
        seed_profiles = [profile for profile in seeds if profile.tier.lower() in allowed_tiers]

        if not seed_profiles:
            # 回退策略：不过滤 priority/tier，确保不会空集，同时记录告警，便于治理
            logger.warning("⚠️ 没有找到符合条件的社区，已回退为不过滤 priority/tier 的抓取集")
            seed_profiles = list(seeds)

        results: List[dict[str, Any]] = []
        semaphore = asyncio.Semaphore(max(1, EFFECTIVE_MAX_CONCURRENCY))

        async def runner(profile: CommunityProfile) -> dict[str, Any]:
            async with semaphore:
                tier_cfg = _tier_settings_for(profile)
                plimit = tier_cfg.post_limit if tier_cfg else DEFAULT_POST_LIMIT
                tfilter = tier_cfg.time_filter if tier_cfg else EFFECTIVE_TIME_FILTER
                svalue = (
                    tier_cfg.pick_sort(default_sort=EFFECTIVE_SORT)
                    if tier_cfg
                    else EFFECTIVE_SORT
                )
                ttl_hours = tier_cfg.hot_cache_ttl_hours if tier_cfg else EFFECTIVE_HOT_CACHE_TTL_HOURS
                # 首次抓取
                result = await _crawl_single(
                    profile.name,
                    settings=settings,
                    cache_manager=cache_manager,
                    reddit_client=reddit_client,
                    post_limit=plimit,
                    time_filter=tfilter,
                    sort=svalue,
                    hot_cache_ttl_hours=ttl_hours,
                    tier_name=profile.tier,
                )
                # 回退策略（Spec009）：若空集则尝试放宽/不过滤
                try:
                    if (
                        result.get("status") == "success"
                        and int(result.get("posts_count", 0) or 0) == 0
                        and tier_cfg is not None
                        and tier_cfg.fallback is not None
                    ):
                        fb = tier_cfg.fallback
                        # 1) 扩大时间窗 / 放宽排序后重试
                        widened = False
                        new_filter = tfilter
                        new_sort = svalue
                        if getattr(fb, "widen_time_filter_to", None):
                            new_filter = str(fb.widen_time_filter_to)
                            widened = True
                        relax = getattr(fb, "relax_sort_mix", None)
                        if isinstance(relax, dict) and relax:
                            # 选择权重最高的排序
                            new_sort = max(relax.items(), key=lambda item: (float(item[1] or 0.0), str(item[0])))[0]
                        if widened or relax:
                            retry1 = await _crawl_single(
                                profile.name,
                                settings=settings,
                                cache_manager=cache_manager,
                                reddit_client=reddit_client,
                                post_limit=plimit,
                                time_filter=new_filter,
                                sort=new_sort,
                                hot_cache_ttl_hours=ttl_hours,
                                tier_name=profile.tier,
                            )
                            if int(retry1.get("posts_count", 0) or 0) > 0:
                                retry1["fallback_applied"] = "widen_or_relax"
                                return retry1
                            result = retry1
                        # 2) 不过滤全集（保底）
                        if getattr(fb, "allow_unfiltered_on_exhausted", False):
                            retry2 = await _crawl_single(
                                profile.name,
                                settings=settings,
                                cache_manager=cache_manager,
                                reddit_client=reddit_client,
                                post_limit=min(120, int(plimit * 1.2)),
                                time_filter="all",
                                sort="top",
                                hot_cache_ttl_hours=ttl_hours,
                                tier_name=profile.tier,
                            )
                            if int(retry2.get("posts_count", 0) or 0) > 0:
                                retry2["fallback_applied"] = "unfiltered_all"
                                return retry2
                            result = retry2
                except Exception as _:
                    # 回退失败不阻断主流程；按原始结果返回
                    pass

                return result

        for batch in _chunked(seed_profiles, EFFECTIVE_BATCH_SIZE):
            batch_results = await asyncio.gather(
                *[runner(profile) for profile in batch],
                return_exceptions=True,
            )
            for profile, outcome in zip(batch, batch_results):
                if isinstance(outcome, Exception):
                    logger.warning("❌ %s: 批量爬取失败 - %s", profile.name, outcome)
                    results.append(
                        {
                            "community": profile.name,
                            "status": "failed",
                            "error": str(outcome),
                        }
                    )
                else:
                    results.append(cast(dict[str, Any], outcome))

        success_count = sum(1 for item in results if item.get("status") == "success")
        failure_count = len(results) - success_count
        rate_limit_hits = sum(1 for item in results if item.get("rate_limited"))
        downgraded = [item.get("community") for item in results if item.get("rate_limited")]
        tier_metrics_payload: dict[str, Any] | None = None

        # ✅ 在返回之前，写入 crawl_metrics 和执行 tier 分配
        async with SessionFactory() as metrics_db:
            # 计算统计指标
            total_new = sum(r.get("posts_count", 0) for r in results if r.get("status") == "success")
            duration_values = [
                float(r.get("duration_seconds", 0))
                for r in results
                if isinstance(r.get("duration_seconds"), (int, float))
            ]
            avg_latency = (
                sum(duration_values) / len(duration_values) if duration_values else 0.0
            )
            empty_count = sum(
                1
                for r in results
                if r.get("status") == "success" and r.get("posts_count", 0) == 0
            )

            # 先计算 tier_assignments
            tier_assignments: dict[str, Any] | None = None
            try:
                scheduler = TieredScheduler(metrics_db)
                tier_assignments = await scheduler.calculate_assignments()
                await scheduler.apply_assignments(tier_assignments)
            except Exception:
                logger.exception("刷新 quality_tier 失败")

            tier_metrics_payload = {
                "assignments": tier_assignments or {},
                "rate_limit_hits": rate_limit_hits,
                "downgraded_communities": [c for c in downgraded if c],
            }

            # 再写入 crawl_metrics（包含 tier_assignments）
            try:
                now = datetime.now(timezone.utc)
                cache_hit_rate = (success_count / max(1, len(seed_profiles))) * 100.0
                logger.info(
                    f"准备写入 crawl_metrics: total={len(seed_profiles)}, success={success_count}, empty={empty_count}, failed={failure_count}"
                )

                # 优先尝试使用 PostgreSQL UPSERT；若不可用（如测试替换了模型或无执行器），则退回 ORM add()
                used_upsert = False
                try:
                    if hasattr(CrawlMetrics, "__table__") or hasattr(CrawlMetrics, "__mapper__"):
                        stmt = pg_insert(CrawlMetrics).values(
                            metric_date=now.date(),
                            metric_hour=now.hour,
                            cache_hit_rate=cache_hit_rate,
                            valid_posts_24h=total_new,
                            total_communities=len(seed_profiles),
                            successful_crawls=success_count,
                            empty_crawls=empty_count,
                            failed_crawls=failure_count,
                            avg_latency_seconds=avg_latency,
                            total_new_posts=total_new,
                            total_updated_posts=0,  # 旧版抓取不支持更新检测
                            total_duplicates=0,      # 旧版抓取不支持去重检测
                            tier_assignments=tier_metrics_payload,
                        )
                        stmt = stmt.on_conflict_do_update(
                            constraint="uq_crawl_metrics_date_hour",
                            set_={
                                "cache_hit_rate": stmt.excluded.cache_hit_rate,
                                "valid_posts_24h": stmt.excluded.valid_posts_24h,
                                "total_communities": stmt.excluded.total_communities,
                                "successful_crawls": CrawlMetrics.successful_crawls + success_count,
                                "empty_crawls": CrawlMetrics.empty_crawls + empty_count,
                                "failed_crawls": CrawlMetrics.failed_crawls + failure_count,
                                "avg_latency_seconds": stmt.excluded.avg_latency_seconds,
                                "total_new_posts": CrawlMetrics.total_new_posts + total_new,
                                "total_updated_posts": CrawlMetrics.total_updated_posts + 0,
                                "total_duplicates": CrawlMetrics.total_duplicates + 0,
                                "tier_assignments": stmt.excluded.tier_assignments,
                            },
                        )
                        await metrics_db.execute(stmt)
                        await metrics_db.commit()
                        logger.info("✅ crawl_metrics upsert 成功")
                        used_upsert = True
                except Exception as exc:
                    logger.warning("crawl_metrics upsert 失败，回退到 add()：%s", exc)

                if not used_upsert:
                    metrics_obj = CrawlMetrics(
                        metric_date=now.date(),
                        metric_hour=now.hour,
                        cache_hit_rate=cache_hit_rate,
                        valid_posts_24h=total_new,
                        total_communities=len(seed_profiles),
                        successful_crawls=success_count,
                        empty_crawls=empty_count,
                        failed_crawls=failure_count,
                        avg_latency_seconds=avg_latency,
                        total_new_posts=total_new,
                        total_updated_posts=0,
                        total_duplicates=0,
                        tier_assignments=tier_metrics_payload,
                    )
                    metrics_db.add(metrics_obj)
                    await metrics_db.commit()
                    logger.info("✅ crawl_metrics 持久化成功（fallback add()）")
            except Exception:
                logger.exception("写入 crawl_metrics 失败")
                try:
                    await metrics_db.rollback()
                except Exception:
                    logger.exception("回滚 crawl_metrics 事务失败")

        return {
            "status": "completed",
            "total": len(seed_profiles),
            "succeeded": success_count,
            "failed": failure_count,
            "communities": results,
            "tier_assignments": tier_metrics_payload or tier_assignments or {},
        }


async def _mark_failure_hit(community_name: str) -> None:
    """标记社区抓取失败次数，使用 AUTOCOMMIT 避免并发冲突"""
    now = datetime.now(timezone.utc)
    async with SessionFactory() as db:
        # 使用 AUTOCOMMIT 隔离级别减少事务竞争
        await db.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await db.execute(
            pg_insert(CommunityCache)
            .values(community_name=community_name, last_crawled_at=now)
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "failure_hit": CommunityCache.failure_hit + 1,
                    "last_attempt_at": now,
                },
            )
        )
        # AUTOCOMMIT 模式下不需要手动 commit
        # await db.commit()


async def _plan_patrol_targets(
    *,
    crawl_run_id: str,
    profiles: list[CommunityProfile],
    force_refresh: bool,
) -> dict[str, Any]:
    """
    巡航心跳 Planner（只下单，不执行）。

    口径（Key 拍板）：
    - 只生成 queued targets（crawler_run_targets），并 enqueue execute_target
    - 只使用增量水位线（last_seen_*），不碰 backfill_floor
    - 每条 target 必须有 idempotency_key（同一轮重复下单不重复插入）
    """
    inserted = 0
    enqueued = 0

    if not profiles:
        return {"inserted": 0, "enqueued": 0}

    # 巡航护栏（Key 拍板）：planner 侧硬上限，防止大社区/配置失误吃穿队列
    patrol_default_posts_limit = int(os.getenv("PATROL_POST_LIMIT", "80"))
    patrol_max_posts_limit = int(os.getenv("PATROL_MAX_POST_LIMIT", "100"))
    patrol_allowed_time_filters = {"hour", "day"}
    max_targets_per_heartbeat = max(1, int(EFFECTIVE_BATCH_SIZE or 1))

    # 统一一次性取水位线快照（用于计划可审计，执行仍以 DB 实时水位线为准）
    sub_keys = [subreddit_key(p.name) for p in profiles]

    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})

        # best-effort: ensure parent run exists (FK safety)
        try:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={"mode": "patrol_planner", "force_refresh": force_refresh},
            )
        except Exception:
            pass

        waterline_rows = await session.execute(
            select(
                CommunityCache.community_name,
                CommunityCache.last_seen_post_id,
                CommunityCache.last_seen_created_at,
            ).where(CommunityCache.community_name.in_(sub_keys))
        )
        waterlines = {
            str(row[0]): (row[1], row[2]) for row in waterline_rows.all() if row[0]
        }

        for profile in profiles:
            if inserted >= max_targets_per_heartbeat:
                break

            # P0 硬规则：跳过 candidate/blocked（最小实现：黑名单/显式 tier/priority）
            tier_norm = str(profile.tier or "").strip().lower()
            prio_norm = str(profile.priority or "").strip().lower()
            if tier_norm in {"candidate", "blocked"} or prio_norm in {"candidate", "blocked"}:
                continue

            sub_key = subreddit_key(profile.name)
            tier_cfg = _tier_settings_for(profile)
            raw_post_limit = int(
                getattr(tier_cfg, "post_limit", 0) if tier_cfg else DEFAULT_POST_LIMIT
            )
            if raw_post_limit <= 0:
                raw_post_limit = patrol_default_posts_limit
            post_limit = max(1, min(patrol_max_posts_limit, raw_post_limit))

            raw_time_filter = str(
                getattr(tier_cfg, "time_filter", "") if tier_cfg else EFFECTIVE_TIME_FILTER
            ).strip().lower()
            # 巡航只抓“新鲜窗口”：允许更窄（hour），但不允许更宽（week/month/year/all）
            time_filter = raw_time_filter if raw_time_filter in patrol_allowed_time_filters else "day"
            sort_value = (
                str(tier_cfg.pick_sort(default_sort=EFFECTIVE_SORT))
                if tier_cfg
                else EFFECTIVE_SORT
            )
            hot_cache_ttl_hours = int(
                tier_cfg.hot_cache_ttl_hours
                if tier_cfg
                else EFFECTIVE_HOT_CACHE_TTL_HOURS
            )

            meta: dict[str, Any] = {
                "tier": str(profile.tier),
                "time_filter": time_filter,
                "sort": sort_value,
                "hot_cache_ttl_hours": hot_cache_ttl_hours,
                "queue": "patrol_queue",
                # 巡航默认不做评论回填；如未来要开，也必须走浅回填配额
                "patrol_comments_enabled": False,
            }
            last_seen_post_id, last_seen_created_at = waterlines.get(sub_key, (None, None))
            if last_seen_post_id:
                meta["cursor_last_seen_post_id"] = str(last_seen_post_id)
            if last_seen_created_at is not None:
                meta["cursor_last_seen_created_at"] = (
                    last_seen_created_at.astimezone(timezone.utc).isoformat()
                    if getattr(last_seen_created_at, "tzinfo", None) is not None
                    else str(last_seen_created_at)
                )

            plan = CrawlPlanContract(
                plan_kind="patrol",
                target_type="subreddit",
                target_value=sub_key,
                reason="cache_expired" if not force_refresh else "manual_force_refresh",
                limits=CrawlPlanLimits(posts_limit=post_limit),
                meta=meta,
            )
            idempotency_key = compute_idempotency_key(plan)
            idempotency_key_human = compute_idempotency_key_human(plan)
            target_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                )
            )

            was_inserted = await ensure_crawler_run_target(
                session,
                community_run_id=target_id,
                crawl_run_id=crawl_run_id,
                subreddit=sub_key,
                status="queued",
                plan_kind=plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                config=plan.model_dump(mode="json"),
            )
            if was_inserted:
                inserted += 1
                if await _enqueue_execute_target_outbox(
                    session=session, target_id=target_id, queue="patrol_queue"
                ):
                    enqueued += 1

        try:
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass

    return {"inserted": inserted, "enqueued": enqueued}


async def _plan_backfill_bootstrap_impl() -> dict[str, Any]:
    """Backfill bootstrap planner (status-driven)."""
    async with _planner_lock("planner:backfill_bootstrap") as acquired:
        if not acquired:
            _MODULE_LOGGER.warning("backfill bootstrap planner skipped: lock busy")
            return {"status": "locked", "inserted": 0, "enqueued": 0}

        now = datetime.now(timezone.utc)
        max_targets = max(0, int(os.getenv("BACKFILL_BOOTSTRAP_MAX_TARGETS", "20")))
        posts_limit = max(
            1, int(os.getenv("BACKFILL_BOOTSTRAP_POSTS_LIMIT", "1000"))
        )
        window_days = max(1, int(os.getenv("BACKFILL_BOOTSTRAP_WINDOW_DAYS", "90")))
        cooldown_minutes = max(
            0, int(os.getenv("BACKFILL_BOOTSTRAP_COOLDOWN_MINUTES", "120"))
        )
        error_cooldown_minutes = max(
            0, int(os.getenv("BACKFILL_ERROR_COOLDOWN_MINUTES", "360"))
        )

        if max_targets == 0:
            return {"status": "disabled", "inserted": 0, "enqueued": 0}

        since_dt = now - timedelta(days=window_days)
        until_dt = now
        cooldown_dt = now - timedelta(minutes=cooldown_minutes)
        error_cooldown_dt = now - timedelta(minutes=error_cooldown_minutes)

        async with SessionFactory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
            rows = await session.execute(
                text(
                    """
                    SELECT c.community_name, c.backfill_cursor
                    FROM community_cache c
                    JOIN community_pool p ON p.name = c.community_name
                    LEFT JOIN crawler_run_targets t
                      ON t.subreddit = c.community_name
                     AND t.plan_kind = 'backfill_posts'
                     AND t.status IN ('queued', 'running')
                    WHERE p.is_active IS TRUE
                      AND p.is_blacklisted IS FALSE
                      AND (
                            c.backfill_status IS NULL
                            OR c.backfill_status IN ('NEEDS', 'ERROR')
                      )
                      AND (
                            c.backfill_status != 'ERROR'
                            OR c.backfill_updated_at IS NULL
                            OR c.backfill_updated_at < :error_cooldown
                      )
                      AND (
                            c.last_attempt_at IS NULL
                            OR c.last_attempt_at < :cooldown
                      )
                      AND t.id IS NULL
                    ORDER BY c.last_attempt_at NULLS FIRST
                    LIMIT :limit
                    """
                ),
                {
                    "cooldown": cooldown_dt,
                    "error_cooldown": error_cooldown_dt,
                    "limit": max_targets,
                },
            )
            targets = [(str(r[0]), r[1]) for r in rows.all() if r[0]]

        if not targets:
            return {"status": "idle", "inserted": 0, "enqueued": 0}

        crawl_run_id = str(uuid.uuid4())
        inserted = 0
        enqueued = 0

        try:
            async with SessionFactory() as run_session:
                await ensure_crawler_run(
                    run_session,
                    crawl_run_id=crawl_run_id,
                    config={
                        "mode": "backfill_bootstrap_planner",
                        "window_days": window_days,
                        "posts_limit": posts_limit,
                    },
                )
                await run_session.commit()
        except Exception:
            pass

        async with SessionFactory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
            for name, cursor_after in targets:
                sub_key = subreddit_key(name)
                meta: dict[str, Any] = {"sort": "new", "queue": BACKFILL_POSTS_QUEUE}
                if cursor_after:
                    meta["cursor_after"] = str(cursor_after)

                plan = CrawlPlanContract(
                    plan_kind="backfill_posts",
                    target_type="subreddit",
                    target_value=sub_key,
                    reason="bootstrap_backfill",
                    window=CrawlPlanWindow(since=since_dt, until=until_dt),
                    limits=CrawlPlanLimits(posts_limit=posts_limit),
                    meta=meta,
                )
                dedupe_key = f"backfill_bootstrap:{sub_key}:{window_days}:{posts_limit}"
                idempotency_key = compute_idempotency_key(plan)
                idempotency_key_human = compute_idempotency_key_human(plan)
                target_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                    )
                )

                was_inserted = await ensure_crawler_run_target(
                    session,
                    community_run_id=target_id,
                    crawl_run_id=crawl_run_id,
                    subreddit=sub_key,
                    status="queued",
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    dedupe_key=dedupe_key,
                    config=plan.model_dump(mode="json"),
                )
                if was_inserted:
                    inserted += 1
                    if await _enqueue_execute_target_outbox(
                        session=session, target_id=target_id, queue=BACKFILL_POSTS_QUEUE
                    ):
                        enqueued += 1

            try:
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

        return {"status": "planned", "inserted": inserted, "enqueued": enqueued}


async def _plan_seed_sampling_impl() -> dict[str, Any]:
    """Seed sampling planner for DONE_CAPPED communities."""
    async with _planner_lock("planner:seed_sampling") as acquired:
        if not acquired:
            _MODULE_LOGGER.warning("seed sampling planner skipped: lock busy")
            return {"status": "locked", "inserted": 0, "enqueued": 0}

        now = datetime.now(timezone.utc)
        cooldown_days = max(1, int(os.getenv("SEED_SAMPLING_COOLDOWN_DAYS", "30")))
        max_targets = max(0, int(os.getenv("SEED_SAMPLING_MAX_TARGETS", "50")))
        posts_limit = max(1, int(os.getenv("SEED_SAMPLING_POSTS_LIMIT", "1000")))
        min_posts = max(
            0, int(os.getenv("SEED_SAMPLING_MIN_POSTS", str(posts_limit)))
        )

        if max_targets == 0:
            return {"status": "disabled", "inserted": 0, "enqueued": 0}

        cooldown_dt = now - timedelta(days=cooldown_days)

        async with SessionFactory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
            rows = await session.execute(
                text(
                    """
                    WITH last_seed AS (
                        SELECT subreddit, MAX(started_at) AS last_seed_at
                        FROM crawler_run_targets
                        WHERE plan_kind IN ('seed_top_year', 'seed_top_all', 'seed_controversial_year')
                          AND status IN ('completed', 'partial')
                        GROUP BY subreddit
                    )
                    SELECT c.community_name
                    FROM community_cache c
                    JOIN community_pool p ON p.name = c.community_name
                    LEFT JOIN last_seed s ON s.subreddit = c.community_name
                    WHERE p.is_active IS TRUE
                      AND p.is_blacklisted IS FALSE
                      AND c.backfill_capped IS TRUE
                      AND COALESCE(c.sample_posts, 0) >= :min_posts
                      AND (s.last_seed_at IS NULL OR s.last_seed_at < :cooldown)
                    ORDER BY s.last_seed_at NULLS FIRST
                    LIMIT :limit
                    """
                ),
                {
                    "cooldown": cooldown_dt,
                    "limit": max_targets,
                    "min_posts": min_posts,
                },
            )
            communities = [str(r[0]) for r in rows.all() if r[0]]

        if not communities:
            return {"status": "idle", "inserted": 0, "enqueued": 0}

        crawl_run_id = str(uuid.uuid4())
        inserted = 0
        enqueued = 0

        try:
            async with SessionFactory() as run_session:
                await ensure_crawler_run(
                    run_session,
                    crawl_run_id=crawl_run_id,
                    config={
                        "mode": "seed_sampling_planner",
                        "cooldown_days": cooldown_days,
                        "posts_limit": posts_limit,
                    },
                )
                await run_session.commit()
        except Exception:
            pass

        async with SessionFactory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        for name in communities:
            sub_key = subreddit_key(name)
            for plan_kind in ("seed_top_year", "seed_top_all"):
                plan = CrawlPlanContract(
                    plan_kind=plan_kind,
                    target_type="subreddit",
                    target_value=sub_key,
                    reason="seed_sampling",
                    limits=CrawlPlanLimits(posts_limit=posts_limit),
                    meta={"queue": BACKFILL_POSTS_QUEUE},
                )
                dedupe_key = f"{plan_kind}:{sub_key}:{posts_limit}"
                idempotency_key = compute_idempotency_key(plan)
                idempotency_key_human = compute_idempotency_key_human(plan)
                target_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                    )
                )
                was_inserted = await ensure_crawler_run_target(
                    session,
                    community_run_id=target_id,
                    crawl_run_id=crawl_run_id,
                    subreddit=sub_key,
                    status="queued",
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    dedupe_key=dedupe_key,
                    config=plan.model_dump(mode="json"),
                )
                if was_inserted:
                    inserted += 1
                    if await _enqueue_execute_target_outbox(
                        session=session, target_id=target_id, queue=BACKFILL_POSTS_QUEUE
                    ):
                        enqueued += 1

            try:
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

        return {"status": "planned", "inserted": inserted, "enqueued": enqueued}


async def _dispatch_task_outbox_impl() -> dict[str, Any]:
    batch_size = max(1, int(os.getenv("TASK_OUTBOX_BATCH_SIZE", "50")))
    max_retries = max(1, int(os.getenv("TASK_OUTBOX_MAX_RETRIES", "5")))

    sent = 0
    skipped = 0
    failed = 0

    async with SessionFactory() as session:
        expected_fingerprint = resolve_outbox_env_fingerprint()
        try:
            current_db = await session.scalar(text("SELECT current_database()"))
        except Exception:
            current_db = "unknown-db"
        rows = await fetch_pending_task_outbox(session, limit=batch_size)
        if not rows:
            logger.info(
                "task_outbox 派发 idle (db=%s fingerprint=%s)",
                current_db,
                expected_fingerprint,
            )
            return {"status": "idle", "sent": 0, "skipped": 0, "failed": 0}
        logger.info(
            "task_outbox 派发选取=%s (db=%s fingerprint=%s)",
            len(rows),
            current_db,
            expected_fingerprint,
        )

        for row in rows:
            outbox_id = str(row.get("id") or "")
            payload = _normalize_outbox_payload(row.get("payload"))
            target_id = str(payload.get("target_id") or "")
            queue = str(payload.get("queue") or COMMENTS_BACKFILL_QUEUE)
            countdown = payload.get("countdown")
            payload_fingerprint = str(payload.get("env_fingerprint") or "")

            if not outbox_id:
                failed += 1
                continue

            if not target_id:
                await mark_task_outbox_failed(
                    session,
                    outbox_id=outbox_id,
                    error="missing_target_id",
                    max_retries=max_retries,
                )
                failed += 1
                continue
            if payload_fingerprint and payload_fingerprint != expected_fingerprint:
                await mark_task_outbox_failed(
                    session,
                    outbox_id=outbox_id,
                    error=f"env_fingerprint_mismatch:{payload_fingerprint}",
                    max_retries=max_retries,
                )
                logger.warning(
                    "task_outbox 指纹不一致 (payload=%s expected=%s)",
                    payload_fingerprint,
                    expected_fingerprint,
                )
                failed += 1
                continue

            target_row = await session.execute(
                text(
                    """
                    SELECT enqueued_at, plan_kind
                    FROM crawler_run_targets
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": target_id},
            )
            target_record = target_row.mappings().first()
            if target_record is None:
                await mark_task_outbox_failed(
                    session,
                    outbox_id=outbox_id,
                    error="target_missing",
                    max_retries=max_retries,
                )
                failed += 1
                continue
            enqueued_at = target_record.get("enqueued_at")
            plan_kind = str(target_record.get("plan_kind") or "")
            if enqueued_at is not None:
                await mark_task_outbox_sent(
                    session, outbox_id=outbox_id, note="already_enqueued"
                )
                skipped += 1
                continue

            if plan_kind == "backfill_posts":
                queue = BACKFILL_POSTS_QUEUE

            try:
                send_kwargs: dict[str, Any] = {
                    "kwargs": {"target_id": target_id},
                    "queue": queue,
                }
                if countdown:
                    send_kwargs["countdown"] = int(countdown)
                celery_app.send_task("tasks.crawler.execute_target", **send_kwargs)

                await session.execute(
                    text(
                        """
                        UPDATE crawler_run_targets
                        SET enqueued_at = now()
                        WHERE id = CAST(:id AS uuid)
                          AND enqueued_at IS NULL
                        """
                    ),
                    {"id": target_id},
                )
                await mark_task_outbox_sent(session, outbox_id=outbox_id)
                sent += 1
            except Exception as exc:
                await mark_task_outbox_failed(
                    session,
                    outbox_id=outbox_id,
                    error=str(exc)[:400],
                    max_retries=max_retries,
                )
                failed += 1

        try:
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass

    return {"status": "sent", "sent": sent, "skipped": skipped, "failed": failed}


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
    crawl_run_id: str | None = None

    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db)
        if force_refresh:
            await loader.load_seed_communities()
            # 强制刷新时，加载所有活跃社区（仍会跳过黑名单）
            seeds = await loader.load_community_pool(force_refresh=True)
            _MODULE_LOGGER.info("🔄 强制刷新模式：下单全量 %s 个社区", len(seeds))
        else:
            # 正常调度：仅下单到期社区
            seeds = await loader.get_due_communities()

        total_pool_count = (await loader.get_pool_stats())["total_communities"]

    # 最小保底：只抓主干 tier（避免 candidate/实验盘混入巡航）
    seed_profiles = [
        profile
        for profile in seeds
        if profile.tier.lower() in ("high", "medium", "low", "gold", "silver", "seed")
    ]
    if not seed_profiles:
        if force_refresh:
            logger.warning("⚠️ 强制刷新后仍未找到符合条件的社区")
        else:
            await _maybe_trigger_probe_hot_fallback(
                due_count=0, total_pool_count=total_pool_count
            )
            logger.info(
                "⏸ 当前没有到期的社区需要抓取（社区总数=%s，全部在冷却中）",
                total_pool_count,
            )
        return {
            "status": "idle",
            "mode": "patrol_planner",
            "run_id": crawl_run_id,
            "total": total_pool_count,
            "due": 0,
            "inserted": 0,
            "enqueued": 0,
        }

    crawl_run_id = str(uuid.uuid4())
    _MODULE_LOGGER.info("🧾 crawl_run_id=%s (本轮巡航心跳批次号)", crawl_run_id)

    if not force_refresh:
        await _maybe_trigger_probe_hot_fallback(
            due_count=len(seed_profiles), total_pool_count=total_pool_count
        )

    # 父级 run（best-effort）
    try:
        async with SessionFactory() as run_session:
            await ensure_crawler_run(
                run_session,
                crawl_run_id=crawl_run_id,
                config={"mode": "patrol_planner", "force_refresh": force_refresh},
            )
            await run_session.commit()
    except Exception:
        pass

    # 可选：按 pain_density 优先级排序（planner 只决定顺序，不抓数据）
    try:
        async with SessionFactory() as metrics_session:
            scheduler = AdaptiveScheduler(metrics_session, lookback_days=30)
            ordered_names, priority_entries = await scheduler.rank(
                [p.name for p in seed_profiles]
            )
            profile_map = {p.name: p for p in seed_profiles}
            seed_profiles = [
                profile_map[name] for name in ordered_names if name in profile_map
            ]
            if priority_entries:
                top_preview = ", ".join(
                    f"{e.name}({e.priority_score:.2f},pain={e.pain_density:.2f})"
                    for e in priority_entries[:5]
                )
                _MODULE_LOGGER.info("📈 自适应排序完成（Top5）：%s", top_preview)
    except Exception:
        _MODULE_LOGGER.exception("自适应排序失败，回退原始顺序")

    plan_stats = await _plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=seed_profiles,
        force_refresh=force_refresh,
    )

    return {
        "status": "planned",
        "mode": "patrol_planner",
        "run_id": crawl_run_id,
        "total": total_pool_count,
        "due": len(seed_profiles),
        **plan_stats,
    }


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
    settings = get_settings()

    async with SessionFactory() as db:
        # 查询低质量社区
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=8)
        from sqlalchemy import and_, select

        result = await db.execute(
            select(CommunityCache.community_name)
            .where(
                and_(
                    CommunityCache.last_crawled_at < cutoff_time,
                    CommunityCache.avg_valid_posts < 50,
                    CommunityCache.is_active == True,  # noqa: E712
                )
            )
            .order_by(CommunityCache.last_crawled_at.asc())
            .limit(50)
        )
        low_quality_communities = result.scalars().all()

    if not low_quality_communities:
        logger.info("✅ 没有需要补抓的低质量社区")
        return {
            "status": "skipped",
            "mode": "low_quality_patrol_planner",
            "total": 0,
            "inserted": 0,
            "enqueued": 0,
        }

    crawl_run_id = str(uuid.uuid4())
    _MODULE_LOGGER.info(
        "🧾 crawl_run_id=%s (低质量社区补抓批次号, planner-only)",
        crawl_run_id,
    )

    # 父级 run（best-effort）
    try:
        async with SessionFactory() as run_session:
            await ensure_crawler_run(
                run_session,
                crawl_run_id=crawl_run_id,
                config={"mode": "low_quality_patrol_planner"},
            )
            await run_session.commit()
    except Exception:
        pass

    inserted = 0
    enqueued = 0

    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})

        for name in low_quality_communities:
            sub_key = subreddit_key(str(name))
            plan = CrawlPlanContract(
                plan_kind="patrol",
                target_type="subreddit",
                target_value=sub_key,
                reason="low_quality_refresh",
                limits=CrawlPlanLimits(posts_limit=100),
                meta={
                    "time_filter": DEFAULT_TIME_FILTER,
                    "sort": DEFAULT_SORT,
                    "hot_cache_ttl_hours": int(EFFECTIVE_HOT_CACHE_TTL_HOURS),
                    "queue": "patrol_queue",
                },
            )
            idempotency_key = compute_idempotency_key(plan)
            idempotency_key_human = compute_idempotency_key_human(plan)
            target_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                )
            )

            was_inserted = await ensure_crawler_run_target(
                session,
                community_run_id=target_id,
                crawl_run_id=crawl_run_id,
                subreddit=sub_key,
                status="queued",
                plan_kind=plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                config=plan.model_dump(mode="json"),
            )
            if was_inserted:
                inserted += 1
                if await _enqueue_execute_target_outbox(
                    session=session, target_id=target_id, queue="patrol_queue"
                ):
                    enqueued += 1

        try:
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass

    logger.info(
        "✅ 低质量社区补抓下单完成: total=%s, inserted=%s, enqueued=%s",
        len(low_quality_communities),
        inserted,
        enqueued,
    )

    return {
        "status": "planned",
        "mode": "low_quality_patrol_planner",
        "run_id": crawl_run_id,
        "total": len(low_quality_communities),
        "inserted": inserted,
        "enqueued": enqueued,
    }


async def _mark_empty_hit(community_name: str) -> None:
    """标记社区空结果次数（用于补抓失败），使用 AUTOCOMMIT 避免并发冲突"""
    now = datetime.now(timezone.utc)
    async with SessionFactory() as db:
        await db.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await db.execute(
            pg_insert(CommunityCache)
            .values(community_name=community_name, last_crawled_at=now)
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "empty_hit": CommunityCache.empty_hit + 1,
                    "last_attempt_at": now,
                },
            )
        )


async def list_stale_caches(threshold_minutes: int = 90) -> List[Tuple[str, datetime]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    async with SessionFactory() as session:
        result = await session.execute(
            CommunityCache.__table__.select().where(
                CommunityCache.last_crawled_at < cutoff
            )
        )
        rows = result.fetchall()
        return [
            (row._mapping["community_name"], row._mapping["last_crawled_at"])
            for row in rows
            if row._mapping["last_crawled_at"] is not None
        ]
    # Fallback if session acquisition failed unexpectedly
    return []


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
