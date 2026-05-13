from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import text

from app.models.business_category import BusinessCategory
from app.models.community_cache import CommunityCache
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_pool import CommunityPool
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.models.semantic_observation import SemanticObservation
from app.services.community.truth_source_sync_service import (
    sync_legacy_truth_for_community,
)


def _unique_subreddit(label: str) -> str:
    return f"r/{label}_{uuid.uuid4().hex[:8]}"


async def _ensure_truth_source_tables(db_session) -> None:
    async with db_session.bind.begin() as conn:
        await conn.run_sync(BusinessCategory.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityRegistry.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityDomainMembership.__table__.create, checkfirst=True)
        await conn.run_sync(
            CommunityGovernanceDecision.__table__.create,
            checkfirst=True,
        )
        await conn.run_sync(CommunityRuntimeState.__table__.create, checkfirst=True)
        await conn.run_sync(SemanticObservation.__table__.create, checkfirst=True)


@pytest.mark.asyncio
async def test_sync_legacy_truth_for_community_creates_new_truth_rows(
    db_session,
) -> None:
    await _ensure_truth_source_tables(db_session)
    community_name = _unique_subreddit("parenting")
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Family_Parenting', 'Family Parenting')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    pool = CommunityPool(
        name=community_name,
        tier="core",
        categories={"categories": ["Family_Parenting"]},
        description_keywords={"keywords": ["sleep"]},
        daily_posts=8,
        avg_comment_length=120,
        quality_score=Decimal("0.88"),
        priority="high",
        is_active=True,
        is_blacklisted=False,
    )
    cache = CommunityCache(
        community_name=community_name,
        last_crawled_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        posts_cached=22,
        ttl_seconds=3600,
        quality_score=Decimal("0.72"),
        hit_count=5,
        crawl_priority=60,
        is_active=True,
        backfill_status="DONE_12M",
        sample_posts=12,
        sample_comments=18,
    )
    cache.last_seen_created_at = datetime(2026, 3, 26, tzinfo=timezone.utc)
    db_session.add(pool)
    await db_session.flush()
    db_session.add(cache)
    await db_session.flush()

    result = await sync_legacy_truth_for_community(
        db_session,
        pool=pool,
        cache=cache,
    )
    await db_session.commit()

    registry = await db_session.get(CommunityRegistry, result.registry_id)
    runtime = await db_session.get(CommunityRuntimeState, result.registry_id)

    assert result.community_name == community_name
    assert result.memberships_written == 1
    assert result.governance_written == 1
    assert registry is not None
    assert registry.legacy_pool_id == pool.id
    assert runtime is not None
    assert runtime.sample_comments == 18


@pytest.mark.asyncio
async def test_sync_legacy_truth_for_community_updates_existing_rows(
    db_session,
) -> None:
    await _ensure_truth_source_tables(db_session)
    community_name = _unique_subreddit("daddit")
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Family_Parenting', 'Family Parenting')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    pool = CommunityPool(
        name=community_name,
        tier="semantic",
        categories={"categories": ["Family_Parenting"]},
        description_keywords={"keywords": ["dad"]},
        daily_posts=2,
        avg_comment_length=80,
        quality_score=Decimal("0.44"),
        priority="medium",
        is_active=True,
        is_blacklisted=False,
    )
    cache = CommunityCache(
        community_name=community_name,
        last_crawled_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        posts_cached=6,
        ttl_seconds=3600,
        quality_score=Decimal("0.41"),
        hit_count=1,
        crawl_priority=25,
        is_active=True,
        backfill_status="NEEDS",
        sample_posts=4,
        sample_comments=3,
    )
    db_session.add(pool)
    await db_session.flush()
    db_session.add(cache)
    await db_session.flush()

    first = await sync_legacy_truth_for_community(db_session, pool=pool, cache=cache)
    await db_session.flush()

    cache.sample_comments = 9
    cache.backfill_status = "DONE_12M"
    second = await sync_legacy_truth_for_community(db_session, pool=pool, cache=cache)
    await db_session.commit()

    runtime = await db_session.get(CommunityRuntimeState, first.registry_id)
    membership_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM community_domain_membership
            WHERE community_id = :community_id
              AND is_current = true
            """
        ),
        {"community_id": first.registry_id},
    )
    governance_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM community_governance_decision
            WHERE membership_id IN (
                SELECT id
                FROM community_domain_membership
                WHERE community_id = :community_id
            )
              AND is_current = true
            """
        ),
        {"community_id": first.registry_id},
    )

    assert second.registry_id == first.registry_id
    assert runtime is not None
    assert runtime.crawl_status == "active"
    assert runtime.sample_comments == 9
    assert membership_count.scalar_one() == 1
    assert governance_count.scalar_one() == 1
