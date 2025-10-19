"""
Tests for IncrementalCrawler metrics tracking (T1.4).

This module tests the monitoring instrumentation added to IncrementalCrawler:
- success_hit: Successful crawls with posts
- empty_hit: Crawls with 0 posts
- failure_hit: API errors
- avg_valid_posts: Rolling average of valid posts
- crawl_metrics: Hourly aggregated metrics
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.crawl_metrics import CrawlMetrics
from app.services.incremental_crawler import IncrementalCrawler


@pytest.mark.asyncio
async def test_crawler_records_success_metrics() -> None:
    """测试成功抓取时记录 success_hit 和更新 avg_valid_posts."""
    # Setup: 创建测试社区
    async with SessionFactory() as db:
        await db.execute(
            text("TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE")
        )
        await db.commit()

        pool = CommunityPool(
            name="r/TestSuccess",
            tier="high",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=50,
            quality_score=Decimal("0.80"),
            priority="high",
        )
        from datetime import datetime, timezone

        cache = CommunityCache(
            community_name="r/TestSuccess",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.80"),
            crawl_priority=80,
            crawl_frequency_hours=2,
            is_active=True,
            success_hit=0,
            empty_hit=0,
            failure_hit=0,
            avg_valid_posts=Decimal("0.00"),
        )
        db.add_all([pool, cache])
        await db.commit()

    # Mock Reddit API to return 10 posts
    from app.services.reddit_client import RedditPost

    mock_posts = [
        RedditPost(
            id=f"post{i}",
            title=f"Test Post {i}",
            selftext="Test content",
            author="testuser",
            created_utc=1697500000 + i,
            score=10,
            num_comments=5,
            url=f"https://reddit.com/r/TestSuccess/comments/post{i}",
            permalink=f"/r/TestSuccess/comments/post{i}",
            subreddit="TestSuccess",
        )
        for i in range(10)
    ]

    with patch("app.services.reddit_client.RedditAPIClient") as MockRedditClient:
        mock_client = AsyncMock()
        mock_client.fetch_subreddit_posts.return_value = mock_posts
        MockRedditClient.return_value = mock_client

        async with SessionFactory() as db:
            crawler = IncrementalCrawler(db=db, reddit_client=mock_client)
            await crawler.crawl_community_incremental("r/TestSuccess")

    # Verify: success_hit incremented, avg_valid_posts updated
    async with SessionFactory() as db:
        stmt = select(CommunityCache).where(
            CommunityCache.community_name == "r/TestSuccess"
        )
        result = await db.execute(stmt)
        cache = result.scalar_one()

        assert cache.success_hit == 1, "success_hit should be incremented"
        assert cache.empty_hit == 0, "empty_hit should remain 0"
        assert cache.failure_hit == 0, "failure_hit should remain 0"
        assert cache.avg_valid_posts > 0, "avg_valid_posts should be updated"


@pytest.mark.asyncio
async def test_crawler_records_empty_metrics() -> None:
    """测试空结果时记录 empty_hit."""
    # Setup: 创建测试社区
    async with SessionFactory() as db:
        await db.execute(
            text("TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE")
        )
        await db.commit()

        pool = CommunityPool(
            name="r/TestEmpty",
            tier="low",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=1,
            quality_score=Decimal("0.30"),
            priority="low",
        )
        cache = CommunityCache(
            community_name="r/TestEmpty",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.30"),
            crawl_priority=30,
            crawl_frequency_hours=24,
            is_active=True,
            success_hit=0,
            empty_hit=0,
            failure_hit=0,
            avg_valid_posts=Decimal("0.00"),
        )
        db.add_all([pool, cache])
        await db.commit()

    # Mock Reddit API to return empty list
    with patch("app.services.reddit_client.RedditAPIClient") as MockRedditClient:
        mock_client = AsyncMock()
        mock_client.fetch_subreddit_posts.return_value = []
        MockRedditClient.return_value = mock_client

        async with SessionFactory() as db:
            crawler = IncrementalCrawler(db=db, reddit_client=mock_client)
            await crawler.crawl_community_incremental("r/TestEmpty")

    # Verify: empty_hit incremented
    async with SessionFactory() as db:
        stmt = select(CommunityCache).where(
            CommunityCache.community_name == "r/TestEmpty"
        )
        result = await db.execute(stmt)
        cache = result.scalar_one()

        assert cache.success_hit == 0, "success_hit should remain 0"
        assert cache.empty_hit == 1, "empty_hit should be incremented"
        assert cache.failure_hit == 0, "failure_hit should remain 0"
        assert cache.avg_valid_posts == 0, "avg_valid_posts should remain 0"


@pytest.mark.asyncio
async def test_crawler_records_failure_metrics() -> None:
    """测试失败时记录 failure_hit."""
    # Setup: 创建测试社区
    async with SessionFactory() as db:
        await db.execute(
            text("TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE")
        )
        await db.commit()

        pool = CommunityPool(
            name="r/TestFailure",
            tier="medium",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=20,
            quality_score=Decimal("0.60"),
            priority="medium",
        )
        cache = CommunityCache(
            community_name="r/TestFailure",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.60"),
            crawl_priority=60,
            crawl_frequency_hours=6,
            is_active=True,
            success_hit=0,
            empty_hit=0,
            failure_hit=0,
            avg_valid_posts=Decimal("0.00"),
        )
        db.add_all([pool, cache])
        await db.commit()

    # Mock Reddit API to raise exception
    with patch("app.services.reddit_client.RedditAPIClient") as MockRedditClient:
        mock_client = AsyncMock()
        mock_client.fetch_subreddit_posts.side_effect = Exception("API Error")
        MockRedditClient.return_value = mock_client

        async with SessionFactory() as db:
            crawler = IncrementalCrawler(db=db, reddit_client=mock_client)
            await crawler.crawl_community_incremental("r/TestFailure")

    # Verify: failure_hit incremented
    async with SessionFactory() as db:
        stmt = select(CommunityCache).where(
            CommunityCache.community_name == "r/TestFailure"
        )
        result = await db.execute(stmt)
        cache = result.scalar_one()

        assert cache.success_hit == 0, "success_hit should remain 0"
        assert cache.empty_hit == 0, "empty_hit should remain 0"
        assert cache.failure_hit == 1, "failure_hit should be incremented"
        assert cache.avg_valid_posts == 0, "avg_valid_posts should remain 0"


@pytest.mark.asyncio
async def test_crawler_writes_crawl_metrics() -> None:
    """测试写入 crawl_metrics 表."""
    # Setup: 创建多个测试社区
    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE community_cache, community_pool, crawl_metrics RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

        for i in range(5):
            pool = CommunityPool(
                name=f"r/Test{i}",
                tier="high",
                categories={"topic": ["test"]},
                description_keywords={"test": 1},
                daily_posts=50,
                quality_score=Decimal("0.80"),
                priority="high",
            )
            cache = CommunityCache(
                community_name=f"r/Test{i}",
                last_crawled_at=datetime.now(timezone.utc),
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.80"),
                crawl_priority=80,
                crawl_frequency_hours=2,
                is_active=True,
                success_hit=0,
                empty_hit=0,
                failure_hit=0,
                avg_valid_posts=Decimal("0.00"),
            )
            db.add_all([pool, cache])
        await db.commit()

    # Mock Reddit API
    from app.services.reddit_client import RedditPost

    with patch("app.services.reddit_client.RedditAPIClient") as MockRedditClient:
        mock_client = AsyncMock()
        mock_client.fetch_subreddit_posts.return_value = [
            RedditPost(
                id="post1",
                title="Test",
                selftext="Content",
                author="user",
                created_utc=1697500000,
                score=10,
                num_comments=5,
                url="https://reddit.com/test",
                permalink="/test",
                subreddit="Test",
            )
        ]
        MockRedditClient.return_value = mock_client

        async with SessionFactory() as db:
            crawler = IncrementalCrawler(db=db, reddit_client=mock_client)
            await crawler.crawl_communities([f"r/Test{i}" for i in range(5)])

    # Verify: crawl_metrics 表有记录
    async with SessionFactory() as db:
        stmt = select(CrawlMetrics)
        result = await db.execute(stmt)
        metrics = result.scalars().all()

        assert len(metrics) > 0, "crawl_metrics should have records"
        metric = metrics[0]
        assert metric.total_communities == 5, "total_communities should be 5"
        assert metric.successful_crawls > 0, "successful_crawls should be > 0"
        assert metric.metric_date == datetime.now(timezone.utc).date()

