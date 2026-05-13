from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import text

from app.services.community.gold_dev_community_restore_service import (
    CommunityCacheSnapshot,
    CommunityPoolSnapshot,
    CommunityRestorePlan,
    apply_community_restore_plan,
)

def _unique_subreddit(label: str) -> str:
    return f"r/{label}_{uuid.uuid4().hex[:8]}"


def _pool_snapshot(name: str, category: str) -> CommunityPoolSnapshot:
    return CommunityPoolSnapshot(
        name=name,
        tier="core",
        categories=[category],
        description_keywords={"keywords": [category.lower()]},
        daily_posts=12,
        avg_comment_length=80,
        quality_score=Decimal("0.88"),
        priority="high",
        user_feedback_count=4,
        discovered_count=2,
        is_active=True,
        is_blacklisted=False,
        blacklist_reason=None,
        downrank_factor=None,
        health_status="healthy",
        last_evaluated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
        auto_tier_enabled=True,
        deleted_at=None,
        deleted_by=None,
    )


def _cache_snapshot(name: str) -> CommunityCacheSnapshot:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return CommunityCacheSnapshot(
        community_name=name,
        last_crawled_at=now,
        posts_cached=22,
        ttl_seconds=3600,
        quality_score=Decimal("0.79"),
        hit_count=8,
        crawl_priority=60,
        last_hit_at=now,
        crawl_frequency_hours=4,
        is_active=True,
        empty_hit=0,
        success_hit=4,
        failure_hit=1,
        avg_valid_posts=12,
        quality_tier="high",
        last_seen_post_id="t3_test",
        last_seen_created_at=now,
        backfill_floor=None,
        backfill_status="DONE_12M",
        coverage_months=12,
        sample_posts=22,
        sample_comments=40,
        backfill_capped=False,
        backfill_cursor=None,
        backfill_cursor_created_at=None,
        backfill_updated_at=now,
        last_attempt_at=now,
        member_count=1200,
        total_posts_fetched=44,
        dedup_rate=Decimal("12.50"),
    )


@pytest.mark.asyncio
async def test_apply_community_restore_plan_persists_and_deactivates(db_session) -> None:
    restore_edc = _unique_subreddit("restore_edc")
    restore_daddit = _unique_subreddit("restore_daddit")
    restore_extra = _unique_subreddit("restore_extra")
    names = [restore_edc, restore_daddit, restore_extra]
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES
              ('Tools_EDC', 'Tools EDC'),
              ('Family_Parenting', 'Family Parenting')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name, tier, categories, description_keywords, daily_posts,
                avg_comment_length, semantic_quality_score, priority, is_active,
                health_status, auto_tier_enabled
            )
            VALUES
              (:restore_edc, 'semantic', '[]'::jsonb, '{}'::jsonb, 1, 1, 0.20, 'low', true, 'warning', true),
              (:restore_extra, 'semantic', '[]'::jsonb, '{}'::jsonb, 1, 1, 0.20, 'low', true, 'warning', true)
            """
        ),
        {"restore_edc": restore_edc, "restore_extra": restore_extra},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_cache (
                community_name, last_crawled_at, posts_cached, ttl_seconds,
                crawl_quality_score, hit_count, crawl_priority, crawl_frequency_hours,
                is_active, empty_hit, success_hit, failure_hit, avg_valid_posts,
                quality_tier, total_posts_fetched
            )
            VALUES
              (:restore_edc, now(), 1, 3600, 0.20, 1, 10, 12, true, 0, 0, 0, 1, 'low', 1),
              (:restore_extra, now(), 1, 3600, 0.20, 1, 10, 12, true, 0, 0, 0, 1, 'low', 1)
            """
        ),
        {"restore_edc": restore_edc, "restore_extra": restore_extra},
    )
    await db_session.commit()
    extra_pool_id = (
        await db_session.execute(
            text("SELECT id FROM community_pool WHERE name = :name"),
            {"name": restore_extra},
        )
    ).scalar_one()
    registry_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO community_registry (
                    platform, community_name, display_name, canonical_url,
                    legacy_pool_id, source_of_truth, is_enabled
                )
                VALUES (
                    'reddit', :community_name, 'restore extra',
                    :canonical_url, :pool_id, 'registry', true
                )
                RETURNING id
                """
            ),
            {
                "pool_id": extra_pool_id,
                "community_name": restore_extra,
                "canonical_url": f"https://reddit.com/{restore_extra}",
            },
        )
    ).scalar_one()
    membership_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO community_domain_membership (
                    community_id, domain_key, membership_source, confidence,
                    is_primary, is_current, evidence, notes
                )
                VALUES (
                    :registry_id, 'Tools_EDC', 'reconciled', 0.500,
                    true, true, '{}'::jsonb, 'legacy extra'
                )
                RETURNING id
                """
            ),
            {"registry_id": registry_id},
        )
    ).scalar_one()
    await db_session.execute(
        text(
            """
            INSERT INTO community_governance_decision (
                membership_id, decision, reason_code, evidence, decided_at, is_current
            )
            VALUES (
                :membership_id, 'approved', 'legacy_active', '{}'::jsonb, now(), true
            )
            """
        ),
        {"membership_id": membership_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_runtime_state (
                community_id, crawl_status, crawl_priority, is_enabled,
                sample_posts, sample_comments, runtime_notes
            )
            VALUES (
                :registry_id, 'active', 50, true, 1, 1, '{}'::jsonb
            )
            """
        ),
        {"registry_id": registry_id},
    )
    await db_session.commit()

    plan = CommunityRestorePlan(
        pool_snapshots=[
            _pool_snapshot(restore_edc, "Tools_EDC"),
            _pool_snapshot(restore_daddit, "Family_Parenting"),
        ],
        cache_snapshots=[
            _cache_snapshot(restore_edc),
            _cache_snapshot(restore_daddit),
        ],
        deactivate_pool_names=[restore_extra],
        deactivate_cache_names=[restore_extra],
    )

    result = await apply_community_restore_plan(
        db_session,
        plan=plan,
        dry_run=False,
    )

    pool_rows = await db_session.execute(
        text(
            """
            SELECT name, categories::text, is_active
            FROM community_pool
            WHERE name = ANY(CAST(:names AS text[]))
            ORDER BY name
            """
        ),
        {"names": names},
    )
    pools = {row[0]: (row[1], row[2]) for row in pool_rows.all()}
    assert pools[restore_edc] == ('["Tools_EDC"]', True)
    assert pools[restore_daddit] == ('["Family_Parenting"]', True)
    assert pools[restore_extra][1] is False

    cache_rows = await db_session.execute(
        text(
            """
            SELECT community_name, is_active
            FROM community_cache
            WHERE community_name = ANY(CAST(:names AS text[]))
            ORDER BY community_name
            """
        ),
        {"names": names},
    )
    caches = {row[0]: row[1] for row in cache_rows.all()}
    assert caches[restore_edc] is True
    assert caches[restore_daddit] is True
    assert caches[restore_extra] is False
    truth_rows = await db_session.execute(
        text(
            """
            SELECT
                r.community_name,
                r.is_enabled,
                s.is_enabled,
                g.decision
            FROM community_registry r
            JOIN community_runtime_state s ON s.community_id = r.id
            JOIN community_domain_membership m ON m.community_id = r.id
            JOIN community_governance_decision g
              ON g.membership_id = m.id
             AND g.is_current = true
            WHERE r.community_name = ANY(CAST(:names AS text[]))
              AND m.is_current = true
            ORDER BY r.community_name
            """
        ),
        {"names": [restore_edc, restore_daddit]},
    )
    assert truth_rows.all() == [
        (restore_daddit, True, True, "approved"),
        (restore_edc, True, True, "approved"),
    ]

    map_rows = await db_session.execute(
        text(
            """
            SELECT m.category_key
            FROM community_category_map m
            JOIN community_pool p ON p.id = m.community_id
            WHERE p.name = :name
            """
        ),
        {"name": restore_edc},
    )
    assert [row[0] for row in map_rows.all()] == ["Tools_EDC"]
    assert result.pool_upserts == 2
    assert result.cache_deactivated == 1
    retired = await db_session.execute(
        text(
            """
            SELECT
                r.is_enabled,
                s.is_enabled,
                s.crawl_status,
                m.is_current,
                g.is_current,
                g.decision
            FROM community_registry r
            JOIN community_runtime_state s ON s.community_id = r.id
            JOIN community_domain_membership m ON m.community_id = r.id
            JOIN community_governance_decision g ON g.membership_id = m.id
            WHERE r.community_name = :name
            """
        ),
        {"name": restore_extra},
    )
    assert retired.one() == (False, False, "paused", False, False, "archived")
    assert result.truth_registry_retired == 1
    assert result.truth_runtime_paused == 1
    assert result.truth_membership_archived == 1
    assert result.truth_governance_archived == 1


@pytest.mark.asyncio
async def test_apply_community_restore_plan_dry_run_rolls_back(db_session) -> None:
    name = _unique_subreddit("restore_dry_run")
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Tools_EDC', 'Tools EDC')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    await db_session.commit()

    plan = CommunityRestorePlan(
        pool_snapshots=[_pool_snapshot(name, "Tools_EDC")],
        cache_snapshots=[_cache_snapshot(name)],
        deactivate_pool_names=[],
        deactivate_cache_names=[],
    )
    result = await apply_community_restore_plan(
        db_session,
        plan=plan,
        dry_run=True,
    )

    pool_count = await db_session.execute(
        text("SELECT COUNT(*) FROM community_pool WHERE name = :name"),
        {"name": name},
    )
    cache_count = await db_session.execute(
        text("SELECT COUNT(*) FROM community_cache WHERE community_name = :name"),
        {"name": name},
    )
    assert result.dry_run is True
    assert result.truth_registry_retired == 0
    assert pool_count.scalar_one() == 0
    assert cache_count.scalar_one() == 0


@pytest.mark.asyncio
async def test_apply_community_restore_plan_bootstraps_missing_business_categories(
    db_session,
) -> None:
    restore_food = _unique_subreddit("restore_food")
    restore_outdoor = _unique_subreddit("restore_outdoor")

    plan = CommunityRestorePlan(
        pool_snapshots=[
            _pool_snapshot(restore_food, "Food_Coffee_Lifestyle"),
            _pool_snapshot(restore_outdoor, "Minimal_Outdoor"),
        ],
        cache_snapshots=[
            _cache_snapshot(restore_food),
            _cache_snapshot(restore_outdoor),
        ],
        deactivate_pool_names=[],
        deactivate_cache_names=[],
    )

    result = await apply_community_restore_plan(
        db_session,
        plan=plan,
        dry_run=False,
    )

    assert result.pool_upserts == 2
    rows = await db_session.execute(
        text(
            """
            SELECT key, is_active
            FROM business_categories
            WHERE key IN ('Food_Coffee_Lifestyle', 'Minimal_Outdoor')
            ORDER BY key
            """
        )
    )
    assert rows.all() == [
        ("Food_Coffee_Lifestyle", True),
        ("Minimal_Outdoor", True),
    ]
    memberships = await db_session.execute(
        text(
            """
            SELECT r.community_name, m.domain_key
            FROM community_domain_membership m
            JOIN community_registry r ON r.id = m.community_id
            WHERE r.community_name IN (:restore_food, :restore_outdoor)
              AND m.is_current = true
            ORDER BY r.community_name
            """
        ),
        {
            "restore_food": restore_food,
            "restore_outdoor": restore_outdoor,
        },
    )
    assert memberships.all() == [
        (restore_food, "Food_Coffee_Lifestyle"),
        (restore_outdoor, "Minimal_Outdoor"),
    ]
