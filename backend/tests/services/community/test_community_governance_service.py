from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.posts_storage import PostRaw
from app.services.community.community_governance_service import (
    CommunityGovernanceService,
)


def _unique_name(label: str) -> str:
    return f"r/{label}_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_governance_snapshot_classifies_effective_candidate_garbage_and_anomaly(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(
        text("TRUNCATE TABLE community_cache, discovered_communities, community_pool RESTART IDENTITY CASCADE")
    )
    await db_session.commit()

    now = datetime.now(timezone.utc)
    effective_name = _unique_name("effective")
    inactive_name = _unique_name("inactive")
    blacklisted_name = _unique_name("blacklisted")
    candidate_name = _unique_name("candidate")
    approved_missing_name = _unique_name("approved_missing")

    db_session.add_all(
        [
            CommunityPool(
                name=effective_name,
                tier="gold",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=10,
                avg_comment_length=50,
                quality_score=0.9,
                priority="high",
                is_active=True,
                is_blacklisted=False,
            ),
            CommunityPool(
                name=inactive_name,
                tier="silver",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=5,
                avg_comment_length=20,
                quality_score=0.5,
                priority="medium",
                is_active=False,
                is_blacklisted=False,
            ),
            CommunityPool(
                name=blacklisted_name,
                tier="silver",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=5,
                avg_comment_length=20,
                quality_score=0.5,
                priority="medium",
                is_active=True,
                is_blacklisted=True,
            ),
            DiscoveredCommunity(
                name=candidate_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
            ),
            DiscoveredCommunity(
                name=effective_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
            ),
            DiscoveredCommunity(
                name=blacklisted_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="rejected",
            ),
            DiscoveredCommunity(
                name=approved_missing_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="approved",
            ),
        ]
    )
    await db_session.commit()

    service = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )
    snapshot = await service.build_snapshot()

    assert [item.name for item in snapshot.effective_communities] == [effective_name]
    assert snapshot.effective_communities[0].normalized_categories == ["ops"]
    assert snapshot.effective_communities[0].category_source == "community_pool.categories"
    assert [item.name for item in snapshot.candidate_communities] == [candidate_name]
    assert snapshot.summary.historical_shell_count == 0
    assert snapshot.summary.effective_unclassified_count == 0
    assert snapshot.summary.category_breakdown == {"ops": 1}

    garbage_pool_names = {item.name for item in snapshot.garbage_communities.pool}
    assert inactive_name in garbage_pool_names
    assert blacklisted_name in garbage_pool_names

    garbage_discovered_names = {item.name for item in snapshot.garbage_communities.discovered}
    assert effective_name in garbage_discovered_names
    assert blacklisted_name in garbage_discovered_names

    anomaly_names = {item.name for item in snapshot.anomalies}
    assert approved_missing_name in anomaly_names


@pytest.mark.asyncio
async def test_governance_cleanup_dev_removes_garbage_and_preserves_effective(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(
        text("TRUNCATE TABLE community_cache, discovered_communities, community_pool RESTART IDENTITY CASCADE")
    )
    await db_session.commit()

    now = datetime.now(timezone.utc)
    effective_name = _unique_name("effective_keep")
    garbage_name = _unique_name("garbage_drop")
    candidate_name = _unique_name("candidate_keep")
    anomaly_name = _unique_name("approved_anomaly")

    db_session.add_all(
        [
            CommunityPool(
                name=effective_name,
                tier="gold",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=12,
                avg_comment_length=60,
                quality_score=0.9,
                priority="high",
                is_active=True,
                is_blacklisted=False,
            ),
            CommunityPool(
                name=garbage_name,
                tier="silver",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=1,
                avg_comment_length=10,
                quality_score=0.3,
                priority="low",
                is_active=False,
                is_blacklisted=False,
            ),
        ]
    )
    await db_session.flush()

    db_session.add_all(
        [
            CommunityCache(
                community_name=effective_name,
                last_crawled_at=now,
                posts_cached=5,
                ttl_seconds=3600,
                quality_score=0.8,
                crawl_priority=50,
                is_active=True,
            ),
            CommunityCache(
                community_name=garbage_name,
                last_crawled_at=now,
                posts_cached=1,
                ttl_seconds=3600,
                quality_score=0.2,
                crawl_priority=10,
                is_active=False,
            ),
            DiscoveredCommunity(
                name=candidate_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
            ),
            DiscoveredCommunity(
                name=effective_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
            ),
            DiscoveredCommunity(
                name=garbage_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="rejected",
            ),
            DiscoveredCommunity(
                name=anomaly_name,
                discovered_from_keywords={"keywords": ["ops"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="approved",
            ),
        ]
    )
    await db_session.commit()

    service = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )

    dry_run = await service.cleanup_dev(dry_run=True)
    assert dry_run.deleted.pool == 1
    assert dry_run.deleted.discovered == 2
    assert dry_run.summary_before.historical_shell_count == 0

    effective_before = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == effective_name)
    )
    garbage_before = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == garbage_name)
    )
    assert effective_before is not None
    assert garbage_before is not None

    executed = await service.cleanup_dev(dry_run=False)
    assert executed.deleted.pool == 1
    assert executed.deleted.cache == 1
    assert executed.deleted.discovered == 2
    assert executed.summary_after is not None
    assert executed.summary_after.historical_shell_count == 0

    effective_after = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == effective_name)
    )
    garbage_after = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == garbage_name)
    )
    candidate_after = await db_session.scalar(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == candidate_name)
    )
    anomaly_after = await db_session.scalar(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == anomaly_name)
    )
    stale_pending_after = await db_session.scalar(
        select(DiscoveredCommunity).where(
            DiscoveredCommunity.name == effective_name,
            DiscoveredCommunity.status == "pending",
        )
    )
    cache_after = await db_session.scalar(
        select(CommunityCache).where(CommunityCache.community_name == garbage_name)
    )

    assert effective_after is not None
    assert garbage_after is None
    assert candidate_after is not None
    assert anomaly_after is not None
    assert stale_pending_after is None
    assert cache_after is None


@pytest.mark.asyncio
async def test_governance_cleanup_dev_skips_pool_rows_with_history_refs(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE community_cache, discovered_communities, posts_raw, community_pool RESTART IDENTITY CASCADE"
        )
    )
    await db_session.commit()

    now = datetime.now(timezone.utc)
    safe_garbage_name = _unique_name("safe_garbage_drop")
    blocked_garbage_name = _unique_name("blocked_garbage_keep")

    safe_garbage = CommunityPool(
        name=safe_garbage_name,
        tier="silver",
        categories={"topic": ["ops"]},
        description_keywords={"keywords": ["ops"]},
        daily_posts=1,
        avg_comment_length=10,
        quality_score=0.2,
        priority="low",
        is_active=False,
        is_blacklisted=False,
    )
    blocked_garbage = CommunityPool(
        name=blocked_garbage_name,
        tier="silver",
        categories={"topic": ["ops"]},
        description_keywords={"keywords": ["ops"]},
        daily_posts=1,
        avg_comment_length=10,
        quality_score=0.2,
        priority="low",
        is_active=False,
        is_blacklisted=False,
    )
    db_session.add_all([safe_garbage, blocked_garbage])
    await db_session.flush()

    db_session.add(
        PostRaw(
            source="reddit",
            source_post_id=f"t3_{uuid.uuid4().hex[:10]}",
            version=1,
            created_at=now,
            author_name="tester",
            title="blocked historical post",
            subreddit=blocked_garbage_name,
            community_id=blocked_garbage.id,
        )
    )
    db_session.add_all(
        [
            CommunityCache(
                community_name=safe_garbage_name,
                last_crawled_at=now,
                posts_cached=1,
                ttl_seconds=3600,
                quality_score=0.2,
                crawl_priority=10,
                is_active=False,
            ),
            CommunityCache(
                community_name=blocked_garbage_name,
                last_crawled_at=now,
                posts_cached=1,
                ttl_seconds=3600,
                quality_score=0.2,
                crawl_priority=10,
                is_active=False,
            ),
        ]
    )
    await db_session.commit()

    service = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )

    snapshot = await service.build_snapshot()
    assert snapshot.summary.pool_garbage_count == 1
    assert snapshot.summary.historical_shell_count == 1
    assert [item.name for item in snapshot.garbage_communities.pool] == [safe_garbage_name]
    assert [item.name for item in snapshot.historical_shells] == [blocked_garbage_name]

    dry_run = await service.cleanup_dev(dry_run=True)
    assert dry_run.deleted.pool == 1
    assert dry_run.deleted.cache == 2
    assert dry_run.blocked.pool == 1
    assert dry_run.summary_before.historical_shell_count == 1
    assert dry_run.targets.pool_names == [safe_garbage_name]
    assert sorted(dry_run.targets.cache_names) == sorted(
        [safe_garbage_name, blocked_garbage_name]
    )
    assert dry_run.targets.historical_shell_names == [blocked_garbage_name]
    assert dry_run.blocked_items.pool[0].name == blocked_garbage_name
    assert dry_run.blocked_items.pool[0].has_posts_raw is True

    executed = await service.cleanup_dev(dry_run=False)
    assert executed.deleted.pool == 1
    assert executed.deleted.cache == 2
    assert executed.blocked.pool == 1
    assert executed.summary_after is not None
    assert executed.summary_after.pool_garbage_count == 0
    assert executed.summary_after.historical_shell_count == 1

    db_session.expire_all()
    safe_after = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == safe_garbage_name)
    )
    blocked_after = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == blocked_garbage_name)
    )
    safe_cache_after = await db_session.scalar(
        select(CommunityCache).where(CommunityCache.community_name == safe_garbage_name)
    )
    blocked_cache_after = await db_session.scalar(
        select(CommunityCache).where(CommunityCache.community_name == blocked_garbage_name)
    )

    assert safe_after is None
    assert blocked_after is not None
    assert safe_cache_after is None
    assert blocked_cache_after is None


@pytest.mark.asyncio
async def test_governance_cleanup_refuses_gold_database(
    db_session: AsyncSession,
) -> None:
    service = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner",
    )

    with pytest.raises(RuntimeError, match="dev/test"):
        await service.cleanup_dev(dry_run=True)


@pytest.mark.asyncio
async def test_governance_cleanup_allows_ci_test_database(
    db_session: AsyncSession,
) -> None:
    service = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_scanner_test",
    )

    result = await service.cleanup_dev(dry_run=True)

    assert result.database == "reddit_scanner_test"
    assert result.dry_run is True


# ── Phase B: 治理合同专项测试 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_snapshot_has_category_source_contract(
    db_session: AsyncSession,
) -> None:
    """B1: build_snapshot 必须在顶层返回 data_source_contract.category_source 字段。"""
    svc = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )
    snapshot = await svc.build_snapshot()

    contract = snapshot.data_source_contract
    assert contract.category_source == "community_pool.categories", (
        f"category_source 应为 community_pool.categories，实际: {contract.category_source}"
    )


@pytest.mark.asyncio
async def test_build_snapshot_historical_shells_have_touch_policy(
    db_session: AsyncSession,
) -> None:
    """B2: historical_shells 每条记录必须包含 touch_policy: do_not_restore_or_activate。"""
    shell_name = _unique_name("shell_b2")
    pool_row = CommunityPool(
        name=shell_name,
        tier="tier3",
        priority="medium",
        categories=["test"],
        description_keywords={"keywords": ["test"]},
        is_active=False,
        is_blacklisted=False,
        deleted_at=None,
    )
    db_session.add(pool_row)
    await db_session.flush()

    db_session.add(
        PostRaw(
            source="reddit",
            source_post_id=f"t3_{uuid.uuid4().hex[:10]}",
            version=1,
            created_at=datetime.now(timezone.utc),
            author_name="tester",
            title="historical shell post",
            subreddit=shell_name,
            community_id=pool_row.id,
        )
    )
    await db_session.commit()

    svc = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )
    snapshot = await svc.build_snapshot()

    shells = snapshot.historical_shells
    our_shells = [s for s in shells if s.name == shell_name]
    assert our_shells, f"社区 {shell_name} 应出现在 historical_shells 中"

    shell = our_shells[0]
    assert shell.touch_policy == "do_not_restore_or_activate", (
        f"touch_policy 应为 do_not_restore_or_activate，实际: {shell.touch_policy}"
    )


@pytest.mark.asyncio
async def test_build_snapshot_normalizes_category_shapes(
    db_session: AsyncSession,
) -> None:
    """社区治理快照必须把 categories 统一成稳定的 normalized_categories，并汇总有效社区分布。"""
    await db_session.execute(
        text("TRUNCATE TABLE community_cache, discovered_communities, community_pool RESTART IDENTITY CASCADE")
    )
    await db_session.commit()

    dict_row = CommunityPool(
        name=_unique_name("dict_categories"),
        tier="gold",
        priority="high",
        categories={"topic": ["ops", "home"], "vertical": "ops"},
        description_keywords={"keywords": ["ops"]},
        is_active=True,
        is_blacklisted=False,
    )
    list_row = CommunityPool(
        name=_unique_name("list_categories"),
        tier="silver",
        priority="medium",
        categories=["family", "Family", "parenting"],
        description_keywords={"keywords": ["family"]},
        is_active=True,
        is_blacklisted=False,
    )
    empty_row = CommunityPool(
        name=_unique_name("empty_categories"),
        tier="silver",
        priority="medium",
        categories=[],
        description_keywords={"keywords": ["misc"]},
        is_active=True,
        is_blacklisted=False,
    )
    db_session.add_all([dict_row, list_row, empty_row])
    await db_session.commit()

    svc = CommunityGovernanceService(
        db_session,
        database_url="postgresql+asyncpg://localhost:5432/reddit_signal_scanner_test",
    )
    snapshot = await svc.build_snapshot()
    items = {item.name: item for item in snapshot.effective_communities}

    assert items[dict_row.name].normalized_categories == ["ops", "home"]
    assert items[list_row.name].normalized_categories == ["family", "parenting"]
    assert items[empty_row.name].normalized_categories == []
    assert items[empty_row.name].category_source == "community_pool.categories"
    assert snapshot.summary.effective_unclassified_count == 1
    assert snapshot.summary.category_breakdown == {
        "family": 1,
        "home": 1,
        "ops": 1,
        "parenting": 1,
        "unclassified": 1,
    }
