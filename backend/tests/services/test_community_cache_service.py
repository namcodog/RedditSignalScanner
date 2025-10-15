from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.community_cache import CommunityCache
from app.services.community_cache_service import upsert_community_cache


@pytest.mark.asyncio
async def test_upsert_creates_entry(db_session):
    await upsert_community_cache(
        "r/testautomation",
        posts_cached=42,
        ttl_seconds=7200,
        quality_score=0.82,
        session=db_session,
    )

    record = await db_session.get(CommunityCache, "r/testautomation")
    assert record is not None
    assert record.posts_cached == 42
    assert record.ttl_seconds == 7200
    assert record.quality_score == Decimal("0.82")


@pytest.mark.asyncio
async def test_upsert_updates_existing(db_session):
    await upsert_community_cache(
        "r/testautomation",
        posts_cached=10,
        ttl_seconds=3600,
        session=db_session,
    )
    await db_session.commit()

    await upsert_community_cache(
        "r/testautomation",
        posts_cached=15,
        ttl_seconds=1800,
        quality_score=0.65,
        session=db_session,
    )
    await db_session.commit()

    record = await db_session.get(CommunityCache, "r/testautomation")
    assert record is not None
    assert record.posts_cached == 15
    assert record.ttl_seconds == 1800
    assert record.quality_score == Decimal("0.65")
