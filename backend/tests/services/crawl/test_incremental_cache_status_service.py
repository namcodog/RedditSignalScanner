from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

import app.services.crawl.incremental_cache_status_service as incremental_status
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


async def _reset_tables() -> None:
    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE community_cache, community_pool RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()


async def _seed_pool(db, name: str, *, tier: str, quality_score: Decimal) -> None:
    db.add(
        CommunityPool(
            name=name,
            tier=tier,
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=3,
            quality_score=quality_score,
            priority=tier,
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_record_incremental_failure_attempt_upserts_cache_row() -> None:
    await _reset_tables()
    now = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)

    async with SessionFactory() as db:
        await _seed_pool(
            db,
            "r/testfailurex",
            tier="medium",
            quality_score=Decimal("0.50"),
        )
        await incremental_status.record_incremental_failure_attempt(
            incremental_status.FailureAttemptInput(
                community_name="r/testfailurex", now=now
            ),
            incremental_status.IncrementalCacheStatusDeps(db=db),
        )
        result = await db.execute(
            select(CommunityCache).where(
                CommunityCache.community_name == "r/testfailurex"
            )
        )
        row = result.scalar_one()
        assert row.failure_hit == 1
        assert row.last_attempt_at == now


@pytest.mark.asyncio
async def test_record_incremental_empty_attempt_increments_empty_hit() -> None:
    await _reset_tables()
    now = datetime(2026, 3, 17, 13, 0, tzinfo=timezone.utc)

    async with SessionFactory() as db:
        await _seed_pool(
            db,
            "r/testemptyx",
            tier="medium",
            quality_score=Decimal("0.40"),
        )
        db.add(
            CommunityCache(
                community_name="r/testemptyx",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.40"),
                crawl_priority=40,
                crawl_frequency_hours=6,
                is_active=True,
                success_hit=0,
                empty_hit=0,
                failure_hit=0,
                avg_valid_posts=Decimal("0.00"),
            )
        )
        await db.commit()

        await incremental_status.record_incremental_empty_attempt(
            incremental_status.EmptyAttemptInput(
                community_name="r/testemptyx", now=now
            ),
            incremental_status.IncrementalCacheStatusDeps(db=db),
        )
        result = await db.execute(
            select(CommunityCache).where(
                CommunityCache.community_name == "r/testemptyx"
            )
        )
        row = result.scalar_one()
        assert row.empty_hit == 1
        assert row.last_crawled_at == now


@pytest.mark.asyncio
async def test_update_incremental_watermark_updates_cursor_and_counts() -> None:
    await _reset_tables()
    now = datetime(2026, 3, 17, 14, 0, tzinfo=timezone.utc)

    async with SessionFactory() as db:
        await _seed_pool(
            db,
            "r/testwatermarkx",
            tier="high",
            quality_score=Decimal("0.90"),
        )
        db.add(
            CommunityCache(
                community_name="r/testwatermarkx",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.90"),
                crawl_priority=90,
                crawl_frequency_hours=2,
                is_active=True,
                success_hit=1,
                empty_hit=0,
                failure_hit=0,
                avg_valid_posts=Decimal("0.00"),
                total_posts_fetched=5,
            )
        )
        await db.commit()

        seen_at = datetime(2026, 3, 17, 13, 30, tzinfo=timezone.utc)
        await incremental_status.update_incremental_watermark(
            incremental_status.WatermarkUpdateInput(
                community_name="r/testwatermarkx",
                last_seen_post_id="p_new",
                last_seen_created_at=seen_at,
                total_fetched=7,
                new_valid_posts=4,
                dedup_rate=25.0,
            ),
            incremental_status.IncrementalCacheStatusDeps(
                db=db, now_factory=lambda: now
            ),
        )
        result = await db.execute(
            select(CommunityCache).where(
                CommunityCache.community_name == "r/testwatermarkx"
            )
        )
        row = result.scalar_one()
        assert row.last_seen_post_id == "p_new"
        assert row.last_seen_created_at == seen_at
        assert row.total_posts_fetched == 12
        assert float(row.dedup_rate) == pytest.approx(25.0)
        assert row.success_hit == 2
        assert row.avg_valid_posts == 4
