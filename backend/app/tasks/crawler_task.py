from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models.community_cache import CommunityCache
from app.services.cache_manager import CacheManager, DEFAULT_CACHE_TTL_SECONDS
from app.services.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.community_cache_service import upsert_community_cache
from app.services.reddit_client import RedditAPIClient, RedditAPIError, RedditPost

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = int(os.getenv("CRAWLER_BATCH_SIZE", "12"))
DEFAULT_MAX_CONCURRENCY = int(os.getenv("CRAWLER_MAX_CONCURRENCY", "5"))
DEFAULT_POST_LIMIT = int(os.getenv("CRAWLER_POST_LIMIT", "100"))


def _chunked(items: Sequence[CommunityProfile], size: int) -> Iterable[Sequence[CommunityProfile]]:
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
    cache_manager.set_cached_posts(community_name, posts)
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
    settings = get_settings()
    loader = CommunityPoolLoader()
    cache_manager = await _build_cache_manager(settings)
    reddit_client = await _build_reddit_client(settings)

    async with reddit_client:
        if force_refresh:
            await loader.import_to_database()

        seeds = await loader.load_community_pool(force_refresh=force_refresh)
        # 爬取所有社区（不限于 seed tier）
        seed_profiles = [profile for profile in seeds if profile.tier.lower() in ("seed", "gold", "silver")]

        if not seed_profiles:
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
                    results.append(outcome)

        success_count = sum(1 for item in results if item.get("status") == "success")
        failure_count = len(results) - success_count
        return {
            "status": "completed",
            "total": len(seed_profiles),
            "succeeded": success_count,
            "failed": failure_count,
            "communities": results,
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


@celery_app.task(name="tasks.crawler.crawl_community", bind=True, max_retries=3)
def crawl_community(self, community_name: str) -> dict[str, Any]:
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


@celery_app.task(name="tasks.crawler.crawl_seed_communities")
def crawl_seed_communities(force_refresh: bool = False) -> dict[str, Any]:
    try:
        return asyncio.run(_crawl_seeds_impl(force_refresh=force_refresh))
    except Exception:  # pragma: no cover - Celery records full traceback
        logger.exception("❌ 种子社区批量爬取失败")
        raise


async def list_stale_caches(threshold_minutes: int = 90) -> List[Tuple[str, datetime]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    async for session in get_session():
        result = await session.execute(
            CommunityCache.__table__.select().where(CommunityCache.last_crawled_at < cutoff)
        )
        rows = result.fetchall()
        return [
            (row["community_name"], row["last_crawled_at"])
            for row in rows
            if row["last_crawled_at"] is not None
        ]
    return []


__all__ = ["crawl_community", "crawl_seed_communities", "list_stale_caches"]
