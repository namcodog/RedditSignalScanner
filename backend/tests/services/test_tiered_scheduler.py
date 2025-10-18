from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.tiered_scheduler import TieredScheduler


@pytest.mark.asyncio
async def test_tiered_scheduler_assignments_and_application() -> None:
    """Tiered scheduler assigns communities based on avg_valid_posts thresholds."""
    # Arrange: seed pool & cache data
    async with SessionFactory() as db:
        await db.execute(text("TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE"))
        await db.commit()

        db.add_all(
            [
                CommunityPool(
                    name="r/TestTier1",
                    tier="high",
                    categories={"topic": ["alpha"]},
                    description_keywords={"alpha": 1},
                    daily_posts=10,
                    quality_score=Decimal("0.90"),
                    priority="high",
                ),
                CommunityPool(
                    name="r/TestTier2",
                    tier="medium",
                    categories={"topic": ["beta"]},
                    description_keywords={"beta": 1},
                    daily_posts=5,
                    quality_score=Decimal("0.70"),
                    priority="medium",
                ),
                CommunityPool(
                    name="r/TestTier3",
                    tier="low",
                    categories={"topic": ["gamma"]},
                    description_keywords={"gamma": 1},
                    daily_posts=2,
                    quality_score=Decimal("0.40"),
                    priority="low",
                ),
            ]
        )
        db.add_all(
            [
                CommunityCache(
                    community_name="r/TestTier1",
                    last_crawled_at=datetime.now(timezone.utc),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.9"),
                    hit_count=0,
                    crawl_priority=90,
                    crawl_frequency_hours=2,
                    is_active=True,
                    avg_valid_posts=Decimal("25.00"),
                ),
                CommunityCache(
                    community_name="r/TestTier2",
                    last_crawled_at=datetime.now(timezone.utc),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.7"),
                    hit_count=0,
                    crawl_priority=60,
                    crawl_frequency_hours=4,
                    is_active=True,
                    avg_valid_posts=Decimal("15.00"),
                ),
                CommunityCache(
                    community_name="r/TestTier3",
                    last_crawled_at=datetime.now(timezone.utc),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.4"),
                    hit_count=0,
                    crawl_priority=30,
                    crawl_frequency_hours=6,
                    is_active=True,
                    avg_valid_posts=Decimal("5.00"),
                ),
            ]
        )
        await db.commit()

    # Act: calculate and apply assignments in a new session
    async with SessionFactory() as db:
        scheduler = TieredScheduler(db)
        assignments = await scheduler.calculate_assignments()
        await scheduler.apply_assignments(assignments)
        tier1_names = await scheduler.get_communities_for_tier("tier1")
        tier2_names = await scheduler.get_communities_for_tier("tier2")
        tier3_names = await scheduler.get_communities_for_tier("tier3")

    # Assert
    assert "r/TestTier1" in assignments["tier1"]
    assert "r/TestTier2" in assignments["tier2"]
    assert "r/TestTier3" in assignments["tier3"]
    assert "r/TestTier1" in tier1_names
    assert "r/TestTier2" in tier2_names
    assert "r/TestTier3" in tier3_names
