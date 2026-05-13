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
from app.services.community.truth_source_batch_service import (
    reconcile_legacy_truth_batch,
)


def _unique_subreddit(label: str) -> str:
    return f"r/{label}_{uuid.uuid4().hex[:8]}"


async def _ensure_truth_tables(db_session) -> None:
    async with db_session.bind.begin() as conn:
        await conn.run_sync(BusinessCategory.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityRegistry.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityDomainMembership.__table__.create, checkfirst=True)
        await conn.run_sync(
            CommunityGovernanceDecision.__table__.create,
            checkfirst=True,
        )
        await conn.run_sync(CommunityRuntimeState.__table__.create, checkfirst=True)


@pytest.mark.asyncio
async def test_reconcile_legacy_truth_batch_dry_run_does_not_persist(
    db_session,
) -> None:
    await _ensure_truth_tables(db_session)
    community_name = _unique_subreddit("newparents")
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Family_Parenting', 'Family Parenting')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    db_session.add(
        CommunityPool(
            name=community_name,
            tier="core",
            categories={"categories": ["Family_Parenting"]},
            description_keywords={},
            daily_posts=2,
            avg_comment_length=10,
            quality_score=Decimal("0.80"),
            priority="high",
            is_active=True,
        )
    )
    await db_session.commit()

    result = await reconcile_legacy_truth_batch(
        db_session,
        dry_run=True,
        community_names=[community_name],
    )

    count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM community_registry
            WHERE community_name = :community_name
            """
        ),
        {"community_name": community_name},
    )
    assert result.synced == 1
    assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_reconcile_legacy_truth_batch_persists_synced_rows(db_session) -> None:
    await _ensure_truth_tables(db_session)
    populated_name = _unique_subreddit("edc")
    empty_name = _unique_subreddit("empty")
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Tools_EDC', 'Tools EDC')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    db_session.add_all(
        [
            CommunityPool(
                name=populated_name,
                tier="core",
                categories={"categories": ["Tools_EDC"]},
                description_keywords={},
                daily_posts=2,
                avg_comment_length=10,
                quality_score=Decimal("0.90"),
                priority="high",
                is_active=True,
            ),
            CommunityPool(
                name=empty_name,
                tier="semantic",
                categories={},
                description_keywords={},
                daily_posts=0,
                avg_comment_length=0,
                quality_score=Decimal("0.10"),
                priority="low",
                is_active=True,
            ),
        ]
    )
    await db_session.flush()
    db_session.add(
        CommunityCache(
            community_name=populated_name,
            last_crawled_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            posts_cached=5,
            ttl_seconds=3600,
            quality_score=Decimal("0.70"),
            hit_count=1,
            crawl_priority=50,
            is_active=True,
            sample_posts=5,
            sample_comments=2,
        )
    )
    await db_session.commit()

    result = await reconcile_legacy_truth_batch(
        db_session,
        dry_run=False,
        community_names=[populated_name, empty_name],
    )

    registry_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM community_registry
            WHERE community_name IN (:populated_name, :empty_name)
            """
        ),
        {
            "populated_name": populated_name,
            "empty_name": empty_name,
        },
    )
    runtime_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM community_runtime_state
            WHERE community_id IN (
                SELECT id
                FROM community_registry
                WHERE community_name IN (:populated_name, :empty_name)
            )
            """
        ),
        {
            "populated_name": populated_name,
            "empty_name": empty_name,
        },
    )
    assert result.scanned == 2
    assert result.synced == 1
    assert result.skipped == 1
    assert registry_count.scalar_one() == 1
    assert runtime_count.scalar_one() == 1
