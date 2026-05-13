from __future__ import annotations

import json
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.business_category_catalog import (
    ensure_business_category_catalog,
)
from app.services.community.community_category_map_service import (
    replace_community_category_map,
)
from app.services.community.gold_dev_community_restore_models import (
    CommunityCacheSnapshot,
    CommunityPoolSnapshot,
    CommunityRestorePlan,
    CommunityRestoreResult,
    load_gold_community_restore_plan,
)
from app.services.community.truth_source_health_guard import (
    assert_restore_truth_health,
    read_truth_source_health_snapshot,
)
from app.services.community.truth_source_sync_service import (
    sync_legacy_truth_for_community,
)


async def _retire_deactivated_truth_rows(
    session: AsyncSession,
    *,
    community_names: list[str],
) -> tuple[int, int, int, int]:
    if not community_names:
        return (0, 0, 0, 0)
    registry_result = await session.execute(
        text(
            """
            UPDATE community_registry
            SET is_enabled = false
            WHERE community_name = ANY(CAST(:names AS text[]))
              AND is_enabled = true
            """
        ),
        {"names": community_names},
    )
    runtime_result = await session.execute(
        text(
            """
            UPDATE community_runtime_state s
                SET is_enabled = false,
                    crawl_status = 'paused'
            FROM community_registry r
            WHERE s.community_id = r.id
              AND r.community_name = ANY(CAST(:names AS text[]))
              AND s.is_enabled = true
            """
        ),
        {"names": community_names},
    )
    membership_result = await session.execute(
        text(
            """
            UPDATE community_domain_membership m
                SET is_current = false,
                    is_primary = false
            FROM community_registry r
            WHERE m.community_id = r.id
              AND r.community_name = ANY(CAST(:names AS text[]))
              AND m.is_current = true
            """
        ),
        {"names": community_names},
    )
    governance_result = await session.execute(
        text(
            """
            UPDATE community_governance_decision g
            SET is_current = false,
                decision = 'archived',
                reason_code = 'legacy_pool_retired'
            FROM community_domain_membership m, community_registry r
            WHERE g.membership_id = m.id
              AND m.community_id = r.id
              AND r.community_name = ANY(CAST(:names AS text[]))
              AND g.is_current = true
            """
        ),
        {"names": community_names},
    )
    return (
        int(registry_result.rowcount or 0),
        int(runtime_result.rowcount or 0),
        int(membership_result.rowcount or 0),
        int(governance_result.rowcount or 0),
    )


async def apply_community_restore_plan(
    session: AsyncSession,
    *,
    plan: CommunityRestorePlan,
    dry_run: bool,
) -> CommunityRestoreResult:
    required_category_keys = sorted(
        {
            category
            for snapshot in plan.pool_snapshots
            for category in snapshot.categories
            if category
        }
    )
    await ensure_business_category_catalog(session, keys=required_category_keys)
    expected_enabled_names = {
        snapshot.name
        for snapshot in plan.pool_snapshots
        if snapshot.is_active
        and any(
            cache.community_name == snapshot.name and cache.is_active
            for cache in plan.cache_snapshots
        )
    }
    existing_pools = {
        row.name: row
        for row in (
            await session.execute(select(CommunityPool).where(CommunityPool.name.in_([p.name for p in plan.pool_snapshots])))
        ).scalars()
    }
    existing_caches = {
        row.community_name: row
        for row in (
            await session.execute(
                select(CommunityCache).where(
                    CommunityCache.community_name.in_([c.community_name for c in plan.cache_snapshots])
                )
            )
        ).scalars()
    }

    for snapshot in plan.pool_snapshots:
        pool = existing_pools.get(snapshot.name)
        if pool is None:
            pool = CommunityPool(
                name=snapshot.name,
                tier=snapshot.tier,
                categories=list(snapshot.categories),
                description_keywords=snapshot.description_keywords,
                daily_posts=snapshot.daily_posts,
                avg_comment_length=snapshot.avg_comment_length,
                quality_score=snapshot.quality_score,
                priority=snapshot.priority,
                user_feedback_count=snapshot.user_feedback_count,
                discovered_count=snapshot.discovered_count,
                is_active=snapshot.is_active,
                is_blacklisted=snapshot.is_blacklisted,
                blacklist_reason=snapshot.blacklist_reason,
                downrank_factor=snapshot.downrank_factor,
                health_status=snapshot.health_status,
                last_evaluated_at=snapshot.last_evaluated_at,
                auto_tier_enabled=snapshot.auto_tier_enabled,
                deleted_at=snapshot.deleted_at,
                deleted_by=snapshot.deleted_by,
            )
            session.add(pool)
            await session.flush()
            existing_pools[snapshot.name] = pool
        else:
            pool.tier = snapshot.tier
            pool.categories = list(snapshot.categories)
            pool.description_keywords = snapshot.description_keywords
            pool.daily_posts = snapshot.daily_posts
            pool.avg_comment_length = snapshot.avg_comment_length
            pool.quality_score = snapshot.quality_score
            pool.priority = snapshot.priority
            pool.user_feedback_count = snapshot.user_feedback_count
            pool.discovered_count = snapshot.discovered_count
            pool.is_active = snapshot.is_active
            pool.is_blacklisted = snapshot.is_blacklisted
            pool.blacklist_reason = snapshot.blacklist_reason
            pool.downrank_factor = snapshot.downrank_factor
            pool.health_status = snapshot.health_status
            pool.last_evaluated_at = snapshot.last_evaluated_at
            pool.auto_tier_enabled = snapshot.auto_tier_enabled
            pool.deleted_at = snapshot.deleted_at
            pool.deleted_by = snapshot.deleted_by
        await replace_community_category_map(
            session,
            community_id=pool.id,
            categories=snapshot.categories,
        )
        await session.execute(text("SET LOCAL app.allow_category_cache_update = '1'"))
        await session.execute(
            text(
                """
                UPDATE community_pool
                SET categories = CAST(:categories AS jsonb)
                WHERE id = :community_id
                """
            ),
            {"community_id": pool.id, "categories": json.dumps(snapshot.categories)},
        )

    for snapshot in plan.cache_snapshots:
        cache = existing_caches.get(snapshot.community_name)
        if cache is None:
            cache = CommunityCache(community_name=snapshot.community_name, last_crawled_at=snapshot.last_crawled_at)
            session.add(cache)
            existing_caches[snapshot.community_name] = cache
        cache.posts_cached = snapshot.posts_cached
        cache.ttl_seconds = snapshot.ttl_seconds
        cache.quality_score = snapshot.quality_score
        cache.hit_count = snapshot.hit_count
        cache.crawl_priority = snapshot.crawl_priority
        cache.last_hit_at = snapshot.last_hit_at
        cache.crawl_frequency_hours = snapshot.crawl_frequency_hours
        cache.is_active = snapshot.is_active
        cache.empty_hit = snapshot.empty_hit
        cache.success_hit = snapshot.success_hit
        cache.failure_hit = snapshot.failure_hit
        cache.avg_valid_posts = snapshot.avg_valid_posts
        cache.quality_tier = snapshot.quality_tier
        cache.last_seen_post_id = snapshot.last_seen_post_id
        cache.last_seen_created_at = snapshot.last_seen_created_at
        cache.backfill_floor = snapshot.backfill_floor
        cache.backfill_status = snapshot.backfill_status
        cache.coverage_months = snapshot.coverage_months
        cache.sample_posts = snapshot.sample_posts
        cache.sample_comments = snapshot.sample_comments
        cache.backfill_capped = snapshot.backfill_capped
        cache.backfill_cursor = snapshot.backfill_cursor
        cache.backfill_cursor_created_at = snapshot.backfill_cursor_created_at
        cache.backfill_updated_at = snapshot.backfill_updated_at
        cache.last_attempt_at = snapshot.last_attempt_at
        cache.member_count = snapshot.member_count
        cache.total_posts_fetched = snapshot.total_posts_fetched
        cache.dedup_rate = snapshot.dedup_rate

    if plan.deactivate_pool_names:
        await session.execute(
            text(
                """
                UPDATE community_pool
                SET is_active = false
                WHERE name = ANY(CAST(:names AS text[]))
                """
            ),
            {"names": plan.deactivate_pool_names},
        )
    if plan.deactivate_cache_names:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET is_active = false
                WHERE community_name = ANY(CAST(:names AS text[]))
                """
            ),
            {"names": plan.deactivate_cache_names},
        )
    # restore 不再依赖“恢复旧表后再额外 reconcile 一次”。
    # 这里同事务把 truth-source 也重建出来，避免中间态继续漂。
    for snapshot in plan.pool_snapshots:
        await sync_legacy_truth_for_community(
            session,
            pool=existing_pools.get(snapshot.name),
            cache=existing_caches.get(snapshot.name),
        )
    (
        truth_registry_retired,
        truth_runtime_paused,
        truth_membership_archived,
        truth_governance_archived,
    ) = await _retire_deactivated_truth_rows(
        session,
        community_names=sorted(
            set(plan.deactivate_pool_names) | set(plan.deactivate_cache_names)
        ),
    )
    post_snapshot = await read_truth_source_health_snapshot(session)
    assert_restore_truth_health(
        post_snapshot,
        expected_enabled_min=len(expected_enabled_names),
        context="gold-dev restore",
    )

    if dry_run:
        await session.rollback()
    else:
        await session.commit()

    return CommunityRestoreResult(
        pool_upserts=len(plan.pool_snapshots),
        cache_upserts=len(plan.cache_snapshots),
        pool_deactivated=len(plan.deactivate_pool_names),
        cache_deactivated=len(plan.deactivate_cache_names),
        truth_registry_retired=truth_registry_retired,
        truth_runtime_paused=truth_runtime_paused,
        truth_membership_archived=truth_membership_archived,
        truth_governance_archived=truth_governance_archived,
        dry_run=dry_run,
    )


__all__ = [
    "CommunityCacheSnapshot",
    "CommunityPoolSnapshot",
    "CommunityRestorePlan",
    "CommunityRestoreResult",
    "apply_community_restore_plan",
    "load_gold_community_restore_plan",
]
