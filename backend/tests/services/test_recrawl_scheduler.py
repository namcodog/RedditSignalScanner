from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.recrawl_scheduler import find_low_quality_candidates


@pytest.mark.asyncio
async def test_find_low_quality_candidates_filters_by_thresholds() -> None:
    """find_low_quality_candidates returns stale + low-quality communities."""
    now = datetime.now(timezone.utc)
    async with SessionFactory() as db:
        await db.execute(text("TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE"))
        await db.commit()

        db.add_all(
            [
                CommunityPool(
                    name="r/recrawl-fresh",
                    tier="high",
                    categories={"topic": ["fresh"]},
                    description_keywords={"fresh": 1},
                    daily_posts=20,
                    quality_score=Decimal("0.80"),
                    priority="high",
                ),
                CommunityPool(
                    name="r/recrawl-stale",
                    tier="medium",
                    categories={"topic": ["stale"]},
                    description_keywords={"stale": 1},
                    daily_posts=5,
                    quality_score=Decimal("0.60"),
                    priority="medium",
                ),
                CommunityPool(
                    name="r/recrawl-blacklisted",
                    tier="low",
                    categories={"topic": ["blacklisted"]},
                    description_keywords={"blacklisted": 1},
                    daily_posts=1,
                    quality_score=Decimal("0.30"),
                    priority="low",
                    is_blacklisted=True,
                ),
            ]
        )
        db.add_all(
            [
                CommunityCache(
                    community_name="r/recrawl-fresh",
                    last_crawled_at=now - timedelta(hours=2),
                    posts_cached=100,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.80"),
                    hit_count=10,
                    crawl_priority=80,
                    crawl_frequency_hours=2,
                    is_active=True,
                    avg_valid_posts=Decimal("80.00"),
                ),
                CommunityCache(
                    community_name="r/recrawl-stale",
                    last_crawled_at=now - timedelta(hours=12),
                    posts_cached=10,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.60"),
                    hit_count=1,
                    crawl_priority=60,
                    crawl_frequency_hours=6,
                    is_active=True,
                    avg_valid_posts=Decimal("10.00"),
                ),
                CommunityCache(
                    community_name="r/recrawl-blacklisted",
                    last_crawled_at=now - timedelta(hours=20),
                    posts_cached=5,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.30"),
                    hit_count=0,
                    crawl_priority=30,
                    crawl_frequency_hours=24,
                    is_active=True,
                    avg_valid_posts=Decimal("5.00"),
                ),
            ]
        )
        await db.commit()

    async with SessionFactory() as db:
        candidates = await find_low_quality_candidates(
            db,
            hours_threshold=8,
            avg_posts_threshold=50,
        )

    assert candidates == ["r/recrawl-stale"]
