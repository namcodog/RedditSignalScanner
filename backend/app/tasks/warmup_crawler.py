"""Warmup Crawler Celery Task.

Crawls seed communities to build initial cache during warmup period.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.cache_manager import CacheManager
from app.services.community_cache_service import upsert_community_cache
from app.services.reddit_client import RedditAPIClient

logger = logging.getLogger(__name__)


@celery_app.task(name="warmup_crawler", bind=True, max_retries=3)  # type: ignore[misc]
def warmup_crawler_task(self: Any, community_name: str | None = None) -> dict[str, Any]:
    """Warmup crawler task - 使用真实 Reddit API 爬取社区数据。

    Args:
        community_name: Optional specific community to crawl. If None, crawls all active communities.

    Returns:
        dict: Crawl statistics
    """
    # 直接调用 crawler_task 中已经工作的逻辑
    from app.tasks.crawler_task import crawl_seed_communities

    logger.info(f"Starting warmup crawler (community={community_name or 'all'})")
    result: dict[str, Any] = crawl_seed_communities(force_refresh=True)
    logger.info(f"Warmup crawler completed: {result}")
    return result


async def _warmup_crawler_async(community_name: str | None = None) -> dict[str, Any]:
    """Async implementation of warmup crawler.

    Args:
        community_name: Optional specific community to crawl

    Returns:
        dict: Crawl statistics
    """
    logger.info(f"Starting warmup crawler (community={community_name or 'all'})")

    stats: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "community_name": community_name,
        "communities_crawled": 0,
        "posts_fetched": 0,
        "errors": 0,
        "completed_at": None,
    }

    # Get database session (simplified - just get one session)
    from app.db.session import SessionFactory

    async with SessionFactory() as db:
        try:
            # Initialize Reddit API client and cache manager
            reddit_client = RedditAPIClient(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                rate_limit=min(58, settings.reddit_rate_limit),
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=settings.reddit_request_timeout_seconds,
                max_concurrency=settings.reddit_max_concurrency,
            )
            cache_manager = CacheManager(
                redis_url=settings.reddit_cache_redis_url,
                cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
            )

            # Get communities to crawl
            if community_name:
                communities = await _get_specific_community(db, community_name)
            else:
                communities = await _get_active_communities(db)

            logger.info(f"Found {len(communities)} communities to crawl")

            # Crawl each community
            for community in communities:
                community_name_str = community.name  # 提前获取名称，避免 session 过期
                try:
                    count = await _crawl_community(
                        db, reddit_client, cache_manager, community
                    )
                    stats["communities_crawled"] = int(stats["communities_crawled"]) + 1
                    stats["posts_fetched"] = int(stats["posts_fetched"]) + int(count)
                except Exception as e:
                    logger.error(f"Error crawling r/{community_name_str}: {e}")
                    stats["errors"] = int(stats["errors"]) + 1

            # Close Reddit client
            await reddit_client.close()

            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Warmup crawler completed: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Warmup crawler failed: {e}")
            stats["errors"] = int(stats["errors"]) + 1
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            raise


async def _get_specific_community(
    db: AsyncSession,
    community_name: str,
) -> list[CommunityPool]:
    """Get specific community from pool.

    Args:
        db: Database session
        community_name: Community name

    Returns:
        list: List containing single community
    """
    stmt = select(CommunityPool).where(
        CommunityPool.name == community_name,
        CommunityPool.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    community = result.scalar_one_or_none()

    if not community:
        raise ValueError(f"Community not found or inactive: {community_name}")

    return [community]


async def _get_active_communities(db: AsyncSession) -> list[CommunityPool]:
    """Get all active communities from pool.

    Args:
        db: Database session

    Returns:
        list: List of active communities
    """
    stmt = (
        select(CommunityPool)
        .where(CommunityPool.is_active == True)  # noqa: E712
        .order_by(CommunityPool.priority.desc())
    )
    result = await db.execute(stmt)
    communities = result.scalars().all()

    return list(communities)


async def _crawl_community(
    db: AsyncSession,
    reddit_client: RedditAPIClient,
    cache_manager: CacheManager,
    community: CommunityPool,
) -> int:
    """Crawl a single community.

    Args:
        db: Database session
        reddit_client: Reddit API client
        community: Community to crawl
    """
    logger.info(f"Crawling r/{community.name}")

    try:
        # Fetch posts from Reddit
        posts = await reddit_client.fetch_subreddit_posts(
            community.name,
            limit=100,
            time_filter="week",
            sort="top",
        )

        logger.info(f"Fetched {len(posts)} posts from r/{community.name}")

        # Store posts in Redis cache
        cache_manager.set_cached_posts(community.name, posts)

        # Upsert community cache metadata in DB
        await upsert_community_cache(
            community_name=community.name,
            posts_cached=len(posts),
            ttl_seconds=settings.reddit_cache_ttl_seconds,
            session=db,
        )

        # Commit changes
        await db.commit()

        logger.info(f"Successfully crawled r/{community.name}")

        return int(len(posts))

    except Exception as e:
        logger.error(f"Error crawling r/{community.name}: {e}")
        await db.rollback()
        raise


async def _update_cache_entry(
    db: AsyncSession,
    community_name: str,
    posts_count: int,
) -> None:
    """Update cache entry for community.

    Args:
        db: Database session
        community_name: Community name
        posts_count: Number of posts fetched
    """
    # Get existing cache entry
    stmt = select(CommunityCache).where(CommunityCache.community_name == community_name)
    result = await db.execute(stmt)
    cache_entry = result.scalar_one_or_none()

    if cache_entry:
        # Update existing entry
        cache_entry.last_crawled_at = datetime.now(timezone.utc)
        cache_entry.posts_cached = posts_count
        cache_entry.hit_count += 1
        logger.info(f"Updated cache entry for r/{community_name}")
    else:
        # Create new entry
        cache_entry = CommunityCache(
            community_name=community_name,
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=posts_count,
            ttl_seconds=3600,  # 1 hour default
            quality_score=0.8,  # Default quality score
            hit_count=1,
            crawl_priority=60,  # Medium priority
            crawl_frequency_hours=4,  # 4 hours default
            is_active=True,
        )
        db.add(cache_entry)
        logger.info(f"Created cache entry for r/{community_name}")


@celery_app.task(name="warmup_crawler_batch", bind=True)  # type: ignore[misc]
def warmup_crawler_batch_task(self: Any, batch_size: int = 10) -> dict[str, Any]:
    """Batch warmup crawler task.

    Crawls communities in batches to avoid overwhelming the system.

    Args:
        batch_size: Number of communities to crawl in this batch

    Returns:
        dict: Batch crawl statistics
    """
    import asyncio

    result = asyncio.run(_warmup_crawler_batch_async(batch_size))
    return result


async def _warmup_crawler_batch_async(batch_size: int = 10) -> dict[str, Any]:
    """Async implementation of batch warmup crawler.

    Args:
        batch_size: Number of communities to crawl

    Returns:
        dict: Batch crawl statistics
    """
    logger.info(f"Starting batch warmup crawler (batch_size={batch_size})")

    stats: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "batch_size": batch_size,
        "communities_crawled": 0,
        "posts_fetched": 0,
        "errors": 0,
        "completed_at": None,
    }

    from app.db.session import SessionFactory

    async with SessionFactory() as db:
        try:
            # Initialize Reddit API client and cache manager
            reddit_client = RedditAPIClient(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                rate_limit=min(58, settings.reddit_rate_limit),
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=settings.reddit_request_timeout_seconds,
                max_concurrency=settings.reddit_max_concurrency,
            )
            cache_manager = CacheManager(
                redis_url=settings.reddit_cache_redis_url,
                cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
            )

            # Get communities that need crawling (oldest last_crawled_at)
            communities = await _get_communities_for_batch(db, batch_size)

            logger.info(f"Found {len(communities)} communities for batch crawl")

            # Crawl each community
            for community in communities:
                try:
                    count = await _crawl_community(
                        db, reddit_client, cache_manager, community
                    )
                    stats["communities_crawled"] = int(stats["communities_crawled"]) + 1
                    stats["posts_fetched"] = int(stats["posts_fetched"]) + int(count)
                except Exception as e:
                    logger.error(f"Error crawling r/{community.name}: {e}")
                    stats["errors"] = int(stats["errors"]) + 1

            # Close Reddit client
            await reddit_client.close()

            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Batch warmup crawler completed: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Batch warmup crawler failed: {e}")
            stats["errors"] = int(stats["errors"]) + 1
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            raise


async def _get_communities_for_batch(
    db: AsyncSession,
    batch_size: int,
) -> list[CommunityPool]:
    """Get communities that need crawling.

    Prioritizes communities with oldest last_crawled_at.

    Args:
        db: Database session
        batch_size: Number of communities to return

    Returns:
        list: List of communities
    """
    # Get cache entries ordered by last_crawled_at
    cache_stmt = (
        select(CommunityCache)
        .where(CommunityCache.is_active == True)  # noqa: E712
        .order_by(CommunityCache.last_crawled_at.asc())
        .limit(batch_size)
    )
    cache_result = await db.execute(cache_stmt)
    cache_entries = cache_result.scalars().all()

    # Get corresponding pool entries
    community_names = [entry.community_name for entry in cache_entries]
    pool_stmt = select(CommunityPool).where(
        CommunityPool.name.in_(community_names),
        CommunityPool.is_active == True,  # noqa: E712
    )
    pool_result = await db.execute(pool_stmt)
    communities = pool_result.scalars().all()

    return list(communities)
