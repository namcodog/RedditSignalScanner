from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Sequence, Tuple, TypeVar, cast

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.crawl_metrics import CrawlMetrics
from app.services.cache_manager import DEFAULT_CACHE_TTL_SECONDS, CacheManager
from app.services.community_cache_service import upsert_community_cache
from app.services.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.incremental_crawler import IncrementalCrawler

T = TypeVar("T")
from app.services.reddit_client import RedditAPIClient, RedditAPIError, RedditPost
from app.services.tiered_scheduler import TieredScheduler

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = int(os.getenv("CRAWLER_BATCH_SIZE", "12"))
# 数据库操作：低并发（2）避免 "concurrent operations are not permitted" 错误
# 参考：https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/gather_orm_statements.html
DEFAULT_MAX_CONCURRENCY = int(os.getenv("CRAWLER_MAX_CONCURRENCY", "2"))
DEFAULT_POST_LIMIT = int(os.getenv("CRAWLER_POST_LIMIT", "100"))
DEFAULT_TIME_FILTER = os.getenv("CRAWLER_TIME_FILTER", "month")  # week/month/year/all
DEFAULT_SORT = os.getenv("CRAWLER_SORT", "top")  # top/new/hot/rising
DEFAULT_HOT_CACHE_TTL_HOURS = int(os.getenv("HOT_CACHE_TTL_HOURS", "24"))


def _chunked(
    items: Sequence[T], size: int
) -> Iterable[Sequence[T]]:
    if size <= 0:
        size = len(items) or 1
    for index in range(0, len(items), size):
        yield items[index : index + size]


async def _build_cache_manager(settings: Settings) -> CacheManager:
    return CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )


async def _build_reddit_client(settings: Settings) -> RedditAPIClient:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RuntimeError("Reddit API credentials are not configured.")

    return RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    )


async def _crawl_single(
    community_name: str,
    *,
    settings: Settings,
    cache_manager: CacheManager,
    reddit_client: RedditAPIClient,
    post_limit: int,
) -> dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    logger.info("开始爬取社区: %s", community_name)

    # Reddit API 期望的不带前缀名称，例如 'Entrepreneur' 而不是 'r/Entrepreneur'
    raw_name = str(community_name).strip()
    api_subreddit = raw_name[2:] if raw_name.lower().startswith("r/") else raw_name

    posts: List[RedditPost] = await reddit_client.fetch_subreddit_posts(
        api_subreddit,
        limit=post_limit,
        time_filter="week",
        sort="top",
    )

    # 内部缓存与数据库仍然使用带前缀的社区名，保证与社区池/键命名一致
    await cache_manager.set_cached_posts(community_name, posts)
    await upsert_community_cache(
        community_name,
        posts_cached=len(posts),
        ttl_seconds=settings.reddit_cache_ttl_seconds or DEFAULT_CACHE_TTL_SECONDS,
        quality_score=None,
    )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("✅ %s: 缓存 %s 个帖子, 耗时 %.2f 秒", community_name, len(posts), duration)

    return {
        "community": community_name,
        "posts_count": len(posts),
        "status": "success",
        "duration_seconds": duration,
    }


async def _crawl_seeds_impl(force_refresh: bool = False) -> dict[str, Any]:
    """旧版抓取：只写 Redis 缓存（保留用于兼容）"""
    settings = get_settings()
    cache_manager = await _build_cache_manager(settings)
    reddit_client = await _build_reddit_client(settings)

    async with reddit_client:
        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            if force_refresh:
                await loader.load_seed_communities()

            seeds = await loader.load_community_pool(force_refresh=force_refresh)
        # 爬取所有活跃社区（high, medium, low 优先级）
        seed_profiles = [
            profile
            for profile in seeds
            if profile.tier.lower() in ("high", "medium", "low")
        ]

        if not seed_profiles:
            logger.warning("⚠️ 没有找到符合条件的社区，检查 tier 字段")
            return {"status": "skipped", "reason": "no_communities_to_crawl"}

        results: List[dict[str, Any]] = []
        semaphore = asyncio.Semaphore(max(1, DEFAULT_MAX_CONCURRENCY))

        async def runner(profile: CommunityProfile) -> dict[str, Any]:
            async with semaphore:
                return await _crawl_single(
                    profile.name,
                    settings=settings,
                    cache_manager=cache_manager,
                    reddit_client=reddit_client,
                    post_limit=DEFAULT_POST_LIMIT,
                )

        for batch in _chunked(seed_profiles, DEFAULT_BATCH_SIZE):
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
                            tier_assignments=tier_assignments,
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
                        tier_assignments=tier_assignments,
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
            "tier_assignments": tier_assignments or {},
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
                    "last_crawled_at": now,
                },
            )
        )
        # AUTOCOMMIT 模式下不需要手动 commit
        # await db.commit()


async def _crawl_seeds_incremental_impl(force_refresh: bool = False) -> dict[str, Any]:
    """新版增量抓取：冷热双写 + 水位线机制"""
    settings = get_settings()
    reddit_client = await _build_reddit_client(settings)

    async with reddit_client:
        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            if force_refresh:
                await loader.load_seed_communities()

            seeds = await loader.load_community_pool(force_refresh=force_refresh)
            seed_profiles = [
                profile
                for profile in seeds
                if profile.tier.lower() in ("high", "medium", "low")
            ]

            if not seed_profiles:
                logger.warning("⚠️ 没有找到符合条件的社区")
                return {"status": "skipped", "reason": "no_communities_to_crawl"}

            # 创建增量抓取器
            results: List[dict[str, Any]] = []
            semaphore = asyncio.Semaphore(max(1, DEFAULT_MAX_CONCURRENCY))

            async def runner(profile: CommunityProfile) -> dict[str, Any]:
                async with semaphore:
                    async with SessionFactory() as crawl_session:
                        # 使用 AUTOCOMMIT 隔离级别减少事务竞争
                        # 参考：https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/gather_orm_statements.html
                        await crawl_session.connection(
                            execution_options={"isolation_level": "AUTOCOMMIT"}
                        )
                        crawler = IncrementalCrawler(
                            db=crawl_session,
                            reddit_client=reddit_client,
                            hot_cache_ttl_hours=DEFAULT_HOT_CACHE_TTL_HOURS,
                        )
                        return await crawler.crawl_community_incremental(
                            profile.name,
                            limit=DEFAULT_POST_LIMIT,
                            time_filter=DEFAULT_TIME_FILTER,
                            sort=DEFAULT_SORT,
                        )

            for batch in _chunked(seed_profiles, DEFAULT_BATCH_SIZE):
                batch_results = await asyncio.gather(
                    *[runner(profile) for profile in batch],
                    return_exceptions=True,
                )
                for profile, outcome in zip(batch, batch_results):
                    if isinstance(outcome, Exception):
                        logger.warning("❌ %s: 增量爬取失败 - %s", profile.name, outcome)
                        # 失败计数（failure_hit += 1）
                        try:
                            await _mark_failure_hit(profile.name)
                        except Exception:
                            logger.exception("计数 failure_hit 失败：%s", profile.name)
                        results.append(
                            {
                                "community": profile.name,
                                "status": "failed",
                                "error": str(outcome),
                            }
                        )
                    else:
                        results.append(cast(dict[str, Any], outcome))

            total_new = sum(r.get("new_posts", 0) for r in results)
            total_updated = sum(r.get("updated_posts", 0) for r in results)
            total_dup = sum(r.get("duplicates", 0) for r in results)
            success_count = sum(1 for r in results if r.get("watermark_updated", False))
            failed_count = sum(1 for r in results if r.get("status") == "failed")
            empty_count = sum(
                1
                for r in results
                if r.get("status") != "failed" and r.get("new_posts", 0) == 0
            )
            duration_values = [
                float(r.get("duration_seconds", 0))
                for r in results
                if isinstance(r.get("duration_seconds"), (int, float))
            ]
            avg_latency = (
                sum(duration_values) / len(duration_values) if duration_values else 0.0
            )

            # 指标监控（T1.3）
            tier_assignments: dict[str, Any] | None = None

            # 先计算 tier_assignments
            try:
                scheduler = TieredScheduler(db)
                tier_assignments = await scheduler.calculate_assignments()
                await scheduler.apply_assignments(tier_assignments)
            except Exception:
                _MODULE_LOGGER.exception("刷新 quality_tier 失败")

            # 再写入 crawl_metrics（包含 tier_assignments）
            try:
                now = datetime.now(timezone.utc)
                cache_hit_rate = (success_count / max(1, len(seed_profiles))) * 100.0
                _MODULE_LOGGER.info(
                    f"准备写入 crawl_metrics: total={len(seed_profiles)}, success={success_count}, empty={empty_count}, failed={failed_count}"
                )

                used_upsert = False
                try:
                    if hasattr(CrawlMetrics, "__table__") or hasattr(CrawlMetrics, "__mapper__"):
                        stmt = pg_insert(CrawlMetrics).values(
                            metric_date=now.date(),
                            metric_hour=now.hour,
                            cache_hit_rate=cache_hit_rate,
                            valid_posts_24h=total_new,  # 暂以本轮新增作为近似，后续在 T1.4/T1.7 优化口径
                            total_communities=len(seed_profiles),
                            successful_crawls=success_count,
                            empty_crawls=empty_count,
                            failed_crawls=failed_count,
                            avg_latency_seconds=avg_latency,
                            total_new_posts=total_new,
                            total_updated_posts=total_updated,
                            total_duplicates=total_dup,
                            tier_assignments=tier_assignments,
                        )
                        stmt = stmt.on_conflict_do_update(
                            constraint="uq_crawl_metrics_date_hour",
                            set_={
                                "cache_hit_rate": stmt.excluded.cache_hit_rate,
                                "valid_posts_24h": stmt.excluded.valid_posts_24h,
                                "total_communities": stmt.excluded.total_communities,
                                "successful_crawls": CrawlMetrics.successful_crawls + success_count,
                                "empty_crawls": CrawlMetrics.empty_crawls + empty_count,
                                "failed_crawls": CrawlMetrics.failed_crawls + failed_count,
                                "avg_latency_seconds": stmt.excluded.avg_latency_seconds,
                                "total_new_posts": CrawlMetrics.total_new_posts + total_new,
                                "total_updated_posts": CrawlMetrics.total_updated_posts + total_updated,
                                "total_duplicates": CrawlMetrics.total_duplicates + total_dup,
                                "tier_assignments": stmt.excluded.tier_assignments,
                            },
                        )
                        await db.execute(stmt)
                        await db.commit()
                        _MODULE_LOGGER.info("✅ crawl_metrics upsert 成功")
                        used_upsert = True
                except Exception as exc:
                    _MODULE_LOGGER.warning("crawl_metrics upsert 失败，回退到 add()：%s", exc)

                if not used_upsert:
                    metrics_obj = CrawlMetrics(
                        metric_date=now.date(),
                        metric_hour=now.hour,
                        cache_hit_rate=cache_hit_rate,
                        valid_posts_24h=total_new,
                        total_communities=len(seed_profiles),
                        successful_crawls=success_count,
                        empty_crawls=empty_count,
                        failed_crawls=failed_count,
                        avg_latency_seconds=avg_latency,
                        total_new_posts=total_new,
                        total_updated_posts=total_updated,
                        total_duplicates=total_dup,
                        tier_assignments=tier_assignments,
                    )
                    db.add(metrics_obj)
                    await db.commit()
                    _MODULE_LOGGER.info("✅ crawl_metrics 持久化成功（fallback add()）")
            except Exception:
                _MODULE_LOGGER.exception("写入 crawl_metrics 失败")
                try:
                    await db.rollback()
                except Exception:
                    _MODULE_LOGGER.exception("回滚 crawl_metrics 事务失败")

            return {
                "status": "completed",
                "mode": "incremental",
                "total": len(seed_profiles),
                "succeeded": success_count,
                "failed": len(results) - success_count,
                "total_new_posts": total_new,
                "total_updated_posts": total_updated,
                "total_duplicates": total_dup,
                "communities": results,
                "tier_assignments": tier_assignments or {},
            }


async def _crawl_single_impl(community_name: str) -> dict[str, Any]:
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
        )


@celery_app.task(name="tasks.crawler.crawl_community", bind=True, max_retries=3)  # type: ignore[misc]
def crawl_community(self: Any, community_name: str) -> dict[str, Any]:
    if not community_name:
        raise ValueError("community_name is required")
    try:
        return asyncio.run(_crawl_single_impl(community_name))
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
        return asyncio.run(_crawl_seeds_impl(force_refresh=force_refresh))
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 种子社区批量爬取失败")
        raise


@celery_app.task(name="tasks.crawler.crawl_seed_communities_incremental")  # type: ignore[misc]
def crawl_seed_communities_incremental(force_refresh: bool = False) -> dict[str, Any]:
    """新版增量抓取任务（冷热双写 + 水位线）"""
    try:
        return asyncio.run(_crawl_seeds_incremental_impl(force_refresh=force_refresh))
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 增量抓取失败")
        raise


async def _crawl_low_quality_communities_impl() -> dict[str, Any]:
    """精准补抓低质量社区（T1.8）

    查询条件：
    - last_crawled_at > 8h（超过 8 小时未抓取）
    - avg_valid_posts < 50（平均有效帖子数低于 50）
    - is_active = True（仅抓取活跃社区）

    失败处理：
    - 失败时回写 empty_hit += 1
    """
    settings = get_settings()
    reddit_client = await _build_reddit_client(settings)

    async with reddit_client:
        async with SessionFactory() as db:
            # 查询低质量社区
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=8)
            from sqlalchemy import select, and_

            result = await db.execute(
                select(CommunityCache.community_name)
                .where(
                    and_(
                        CommunityCache.last_crawled_at < cutoff_time,
                        CommunityCache.avg_valid_posts < 50,
                        CommunityCache.is_active == True,
                    )
                )
                .order_by(CommunityCache.last_crawled_at.asc())
                .limit(50)  # 每次最多补抓 50 个社区
            )
            low_quality_communities = result.scalars().all()

            if not low_quality_communities:
                logger.info("✅ 没有需要补抓的低质量社区")
                return {
                    "status": "skipped",
                    "reason": "no_low_quality_communities",
                    "total": 0,
                }

            logger.info(f"🎯 发现 {len(low_quality_communities)} 个低质量社区需要补抓")

            # 创建增量抓取器
            results: List[dict[str, Any]] = []
            semaphore = asyncio.Semaphore(max(1, DEFAULT_MAX_CONCURRENCY))

            async def runner(community_name: str) -> dict[str, Any]:
                async with semaphore:
                    async with SessionFactory() as crawl_session:
                        await crawl_session.connection(
                            execution_options={"isolation_level": "AUTOCOMMIT"}
                        )
                        crawler = IncrementalCrawler(
                            db=crawl_session,
                            reddit_client=reddit_client,
                            hot_cache_ttl_hours=DEFAULT_HOT_CACHE_TTL_HOURS,
                        )
                        return await crawler.crawl_community_incremental(
                            community_name,
                            limit=DEFAULT_POST_LIMIT,
                            time_filter=DEFAULT_TIME_FILTER,
                            sort=DEFAULT_SORT,
                        )

            # 分批抓取
            community_list: list[str] = list(low_quality_communities)
            for batch in _chunked(community_list, DEFAULT_BATCH_SIZE):
                batch_results = await asyncio.gather(
                    *[runner(name) for name in batch],
                    return_exceptions=True,
                )
                for community_name, outcome in zip(batch, batch_results):
                    if isinstance(outcome, Exception):
                        logger.warning("❌ %s: 补抓失败 - %s", community_name, outcome)
                        # 失败时回写 empty_hit += 1
                        try:
                            await _mark_empty_hit(community_name)
                        except Exception:
                            logger.exception("回写 empty_hit 失败：%s", community_name)
                        results.append(
                            {
                                "community": community_name,
                                "status": "failed",
                                "error": str(outcome),
                            }
                        )
                    else:
                        results.append(cast(dict[str, Any], outcome))

            # 统计结果
            total_new = sum(r.get("new_posts", 0) for r in results)
            total_updated = sum(r.get("updated_posts", 0) for r in results)
            success_count = sum(1 for r in results if r.get("watermark_updated", False))
            failed_count = sum(1 for r in results if r.get("status") == "failed")
            empty_count = sum(
                1
                for r in results
                if r.get("status") != "failed" and r.get("new_posts", 0) == 0
            )

            logger.info(
                f"✅ 低质量社区补抓完成: 总数={len(low_quality_communities)}, "
                f"成功={success_count}, 失败={failed_count}, 空结果={empty_count}, "
                f"新增帖子={total_new}"
            )

            return {
                "status": "completed",
                "mode": "low_quality_补抓",
                "total": len(low_quality_communities),
                "succeeded": success_count,
                "failed": failed_count,
                "empty": empty_count,
                "total_new_posts": total_new,
                "total_updated_posts": total_updated,
                "communities": results,
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
                    "last_crawled_at": now,
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
        return asyncio.run(_crawl_low_quality_communities_impl())
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 低质量社区补抓失败")
        raise


__all__ = [
    "crawl_community",
    "crawl_seed_communities",
    "crawl_seed_communities_incremental",
    "crawl_low_quality_communities",
    "list_stale_caches",
]
