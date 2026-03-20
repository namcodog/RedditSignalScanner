from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.crawl_metrics import CrawlMetrics
from app.models.posts_storage import PostHot
from app.services.crawl.crawl_metrics_service import (
    CrawlMetricsDeps,
    CrawlMetricsInput,
    record_crawl_metrics,
)


async def _reset_tables() -> None:
    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE posts_hot, community_cache, community_pool, crawl_metrics RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_record_crawl_metrics_creates_hourly_row() -> None:
    await _reset_tables()
    now = datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc)

    async with SessionFactory() as db:
        db.add_all(
            [
                CommunityPool(
                    name="r/metrics_a",
                    tier="high",
                    categories={"topic": ["test"]},
                    description_keywords={"test": 1},
                    daily_posts=12,
                    quality_score=Decimal("0.80"),
                    priority="high",
                ),
                CommunityPool(
                    name="r/metrics_b",
                    tier="high",
                    categories={"topic": ["test"]},
                    description_keywords={"test": 1},
                    daily_posts=8,
                    quality_score=Decimal("0.70"),
                    priority="high",
                ),
            ]
        )
        db.add_all(
            [
                CommunityCache(
                    community_name="r/metrics_a",
                    last_crawled_at=now,
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
                ),
                CommunityCache(
                    community_name="r/metrics_b",
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.70"),
                    crawl_priority=70,
                    crawl_frequency_hours=4,
                    is_active=True,
                    success_hit=0,
                    empty_hit=0,
                    failure_hit=0,
                    avg_valid_posts=Decimal("0.00"),
                ),
            ]
        )
        db.add_all(
            [
                PostHot(
                    source="reddit",
                    source_post_id="hot-1",
                    created_at=now - timedelta(hours=1),
                    cached_at=now - timedelta(hours=1),
                    expires_at=now + timedelta(hours=5),
                    author_id="u1",
                    author_name="u1",
                    title="T1",
                    body="Body",
                    subreddit="r/metrics_a",
                    score=5,
                    num_comments=1,
                    extra_data={"permalink": "/p1"},
                ),
                PostHot(
                    source="reddit",
                    source_post_id="hot-2",
                    created_at=now - timedelta(hours=30),
                    cached_at=now - timedelta(hours=30),
                    expires_at=now - timedelta(hours=1),
                    author_id="u2",
                    author_name="u2",
                    title="T2",
                    body="Body",
                    subreddit="r/metrics_b",
                    score=3,
                    num_comments=2,
                    extra_data={"permalink": "/p2"},
                ),
            ]
        )
        await db.commit()

        await record_crawl_metrics(
            metrics_input=CrawlMetricsInput(
                successful_crawls=2,
                empty_crawls=1,
                failed_crawls=0,
                total_new_posts=8,
                total_updated_posts=2,
                total_duplicates=5,
                avg_latency_seconds=1.25,
            ),
            deps=CrawlMetricsDeps(db=db, now_factory=lambda: now),
        )

        result = await db.execute(select(CrawlMetrics))
        row = result.scalar_one()
        assert row.metric_date == now.date()
        assert row.metric_hour == now.hour
        assert row.valid_posts_24h == 1
        assert row.total_communities == 2
        assert row.successful_crawls == 2
        assert row.empty_crawls == 1
        assert row.failed_crawls == 0
        assert row.total_new_posts == 8
        assert row.total_updated_posts == 2
        assert row.total_duplicates == 5
        assert float(row.cache_hit_rate) == pytest.approx(5 / 15 * 100, rel=1e-3)


@pytest.mark.asyncio
async def test_record_crawl_metrics_accumulates_existing_hourly_row() -> None:
    await _reset_tables()
    now = datetime(2026, 3, 17, 11, 0, tzinfo=timezone.utc)

    async with SessionFactory() as db:
        db.add(
            CommunityPool(
                name="r/metrics_c",
                tier="high",
                categories={"topic": ["test"]},
                description_keywords={"test": 1},
                daily_posts=10,
                quality_score=Decimal("0.90"),
                priority="high",
            )
        )
        db.add(
            CommunityCache(
                community_name="r/metrics_c",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.90"),
                crawl_priority=90,
                crawl_frequency_hours=2,
                is_active=True,
                success_hit=0,
                empty_hit=0,
                failure_hit=0,
                avg_valid_posts=Decimal("0.00"),
            )
        )
        db.add(
            CrawlMetrics(
                metric_date=now.date(),
                metric_hour=now.hour,
                cache_hit_rate=10.0,
                valid_posts_24h=4,
                total_communities=1,
                successful_crawls=1,
                empty_crawls=0,
                failed_crawls=1,
                avg_latency_seconds=2.0,
                total_new_posts=3,
                total_updated_posts=1,
                total_duplicates=2,
            )
        )
        await db.commit()

        await record_crawl_metrics(
            metrics_input=CrawlMetricsInput(
                successful_crawls=2,
                empty_crawls=1,
                failed_crawls=0,
                total_new_posts=5,
                total_updated_posts=4,
                total_duplicates=1,
                avg_latency_seconds=0.8,
            ),
            deps=CrawlMetricsDeps(db=db, now_factory=lambda: now),
        )

        result = await db.execute(select(CrawlMetrics))
        row = result.scalar_one()
        assert row.successful_crawls == 3
        assert row.empty_crawls == 1
        assert row.failed_crawls == 1
        assert row.total_new_posts == 8
        assert row.total_updated_posts == 5
        assert row.total_duplicates == 3
        assert float(row.avg_latency_seconds) == pytest.approx(0.8)
