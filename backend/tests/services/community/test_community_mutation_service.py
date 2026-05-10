from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_pool import CommunityPool
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.community.community_mutation_service import CommunityMutationService


@pytest.mark.asyncio
async def test_upsert_effective_community_writes_truth_and_projection(
    db_session: AsyncSession,
) -> None:
    community_name = f"r/mutation_{uuid.uuid4().hex[:8]}"
    service = CommunityMutationService(db_session)

    result = await service.upsert_effective_community(
        community_name=community_name,
        categories=["Tools_EDC"],
        tier="silver",
        priority="high",
        description_keywords={"keywords": ["knife", "gear"]},
        quality_score=0.82,
        discovered_count=3,
        actor_id=None,
        source_of_truth="manual",
        notes="seeded by test",
    )
    await db_session.commit()

    assert result.community_name == community_name
    assert result.decision == "approved"
    assert result.runtime_enabled is True
    assert result.categories == ["Tools_EDC"]

    registry = (
        await db_session.execute(
            select(CommunityRegistry).where(
                CommunityRegistry.community_name == community_name
            )
        )
    ).scalar_one()
    assert registry.is_enabled is True

    runtime = await db_session.get(CommunityRuntimeState, registry.id)
    assert runtime is not None
    assert runtime.is_enabled is True
    assert runtime.crawl_status == "needs_backfill"
    assert runtime.legacy_cache_name == community_name

    memberships = (
        await db_session.execute(
            select(CommunityDomainMembership).where(
                CommunityDomainMembership.community_id == registry.id,
                CommunityDomainMembership.is_current.is_(True),
            )
        )
    ).scalars().all()
    assert [row.domain_key for row in memberships] == ["Tools_EDC"]

    governance = (
        await db_session.execute(
            select(CommunityGovernanceDecision).where(
                CommunityGovernanceDecision.membership_id == memberships[0].id,
                CommunityGovernanceDecision.is_current.is_(True),
            )
        )
    ).scalar_one()
    assert governance.decision == "approved"

    pool = (
        await db_session.execute(
            select(CommunityPool).where(CommunityPool.name == community_name)
        )
    ).scalar_one()
    assert pool.is_active is True
    assert pool.tier == "silver"
    assert pool.priority == "high"

    cache = await db_session.get(CommunityCache, community_name)
    assert cache is not None
    assert cache.is_active is True
    assert cache.crawl_priority == 90


@pytest.mark.asyncio
async def test_archive_community_disables_truth_and_projection(
    db_session: AsyncSession,
) -> None:
    community_name = f"r/archive_{uuid.uuid4().hex[:8]}"
    service = CommunityMutationService(db_session)

    await service.upsert_effective_community(
        community_name=community_name,
        categories=["Family_Parenting"],
        tier="medium",
        priority="medium",
        description_keywords={"keywords": ["baby", "sleep"]},
        quality_score=0.66,
        discovered_count=1,
        actor_id=None,
        source_of_truth="manual",
    )
    await db_session.commit()

    result = await service.archive_community(
        community_name=community_name,
        actor_id=None,
        reason_code="admin_disabled",
        notes="disabled by test",
    )
    await db_session.commit()
    db_session.expire_all()

    assert result.community_name == community_name
    assert result.decision == "archived"
    assert result.runtime_enabled is False

    registry = (
        await db_session.execute(
            select(CommunityRegistry).where(
                CommunityRegistry.community_name == community_name
            )
        )
    ).scalar_one()
    runtime = await db_session.get(CommunityRuntimeState, registry.id)
    assert runtime is not None
    assert runtime.is_enabled is False
    assert runtime.crawl_status == "paused"

    membership = (
        await db_session.execute(
            select(CommunityDomainMembership).where(
                CommunityDomainMembership.community_id == registry.id,
                CommunityDomainMembership.is_current.is_(True),
            )
        )
    ).scalar_one()
    governance = (
        await db_session.execute(
            select(CommunityGovernanceDecision).where(
                CommunityGovernanceDecision.membership_id == membership.id,
                CommunityGovernanceDecision.is_current.is_(True),
            )
        )
    ).scalar_one()
    assert governance.decision == "archived"
    assert governance.reason_code == "admin_disabled"

    pool = (
        await db_session.execute(
            select(CommunityPool).where(CommunityPool.name == community_name)
        )
    ).scalar_one()
    assert pool.is_active is False
    assert pool.deleted_at is not None

    cache = await db_session.get(CommunityCache, community_name)
    assert cache is not None
    assert cache.is_active is False


@pytest.mark.asyncio
async def test_archive_community_ignores_non_canonical_pool_categories(
    db_session: AsyncSession,
) -> None:
    community_name = f"r/legacy_{uuid.uuid4().hex[:8]}"
    db_session.add(
        CommunityPool(
            name=community_name,
            tier="candidate",
            categories={"topic": ["legacy"]},
            description_keywords={"keywords": ["legacy"]},
            daily_posts=0,
            avg_comment_length=0,
            quality_score=0.4,
            priority="low",
            user_feedback_count=0,
            discovered_count=1,
            is_active=True,
        )
    )
    await db_session.commit()

    result = await CommunityMutationService(db_session).archive_community(
        community_name=community_name,
        actor_id=None,
        reason_code="legacy_cleanup",
    )
    await db_session.commit()
    db_session.expire_all()

    assert result.decision == "archived"
    assert result.categories == []

    pool = (
        await db_session.execute(
            select(CommunityPool).where(CommunityPool.name == community_name)
        )
    ).scalar_one()
    assert pool.is_active is False
