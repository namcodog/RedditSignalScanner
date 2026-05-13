from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.dev_truth_source_compaction_service import (
    compact_dev_truth_source,
)


async def _seed_registry(session: AsyncSession, *, name: str, enabled: bool) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO community_registry (
                        platform, community_name, display_name, canonical_url,
                        source_of_truth, is_enabled
                    )
                    VALUES ('reddit', :name, :name, :url, 'registry', :enabled)
                    RETURNING id
                    """
                ),
                {"name": name, "url": f"https://reddit.com/{name}", "enabled": enabled},
            )
        ).scalar_one()
    )


async def _truncate_existing_tables(
    session: AsyncSession,
    truncate_tables: Callable[..., Awaitable[None]],
    *table_names: str,
) -> None:
    existing: list[str] = []
    for table_name in table_names:
        result = await session.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{table_name}"},
        )
        if result.scalar_one() is not None:
            existing.append(table_name)
    await truncate_tables(*existing)


@pytest.mark.asyncio
async def test_compact_dev_truth_source_deletes_only_safe_rows(
    db_session: AsyncSession,
    async_truncate_test_tables,
) -> None:
    await _truncate_existing_tables(
        db_session,
        async_truncate_test_tables,
        "community_governance_decision",
        "community_domain_membership",
        "community_runtime_state",
        "community_registry",
        "community_category_map",
        "community_audit",
        "posts_raw",
        "community_cache",
        "community_pool",
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name,
                tier,
                categories,
                description_keywords,
                daily_posts,
                avg_comment_length,
                semantic_quality_score,
                priority,
                user_feedback_count,
                discovered_count,
                is_active,
                is_blacklisted,
                health_status,
                auto_tier_enabled
            )
            VALUES
              (
                'r/keep_posts', 'silver', '[]'::jsonb, '{}'::jsonb,
                0, 0, 0.50, 'medium', 0, 0, false, false, 'unknown', true
              ),
              (
                'r/delete_pool', 'silver', '[]'::jsonb, '{}'::jsonb,
                0, 0, 0.50, 'medium', 0, 0, false, false, 'unknown', true
              )
            """
        )
    )
    keep_pool_id = int(
        (
            await db_session.execute(
                text("SELECT id FROM community_pool WHERE name = 'r/keep_posts'")
            )
        ).scalar_one()
    )
    delete_pool_id = int(
        (
            await db_session.execute(
                text("SELECT id FROM community_pool WHERE name = 'r/delete_pool'")
            )
        ).scalar_one()
    )
    await db_session.execute(
        text(
            """
            INSERT INTO posts_raw (
                source, source_post_id, version, created_at, fetched_at, valid_from, is_current,
                title, body, subreddit, community_id, author_name
            )
            VALUES (
                'reddit', 'p1', 1, :ts, :ts, :ts, true,
                'title', 'body', 'r/keep_posts', :community_id, 'tester'
            )
            """
        ),
        {"ts": datetime.now(timezone.utc), "community_id": keep_pool_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_category_map (community_id, category_key, is_primary)
            VALUES (:community_id, 'Tools_EDC', true)
            """
        ),
        {"community_id": delete_pool_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_cache (
                community_name,
                last_crawled_at,
                posts_cached,
                ttl_seconds,
                crawl_quality_score,
                hit_count,
                crawl_priority,
                crawl_frequency_hours,
                is_active,
                empty_hit,
                success_hit,
                failure_hit,
                avg_valid_posts,
                quality_tier,
                total_posts_fetched
            )
            VALUES (
                'r/delete_cache',
                :ts,
                0,
                3600,
                0.50,
                0,
                50,
                2,
                false,
                0,
                0,
                0,
                0,
                'medium',
                0
            )
            """
        ),
        {"ts": datetime.now(timezone.utc)},
    )
    disabled_registry = await _seed_registry(
        db_session,
        name="r/disabled_registry",
        enabled=False,
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_runtime_state (
                community_id, crawl_status, crawl_priority, is_enabled,
                sample_posts, sample_comments, runtime_notes
            )
            VALUES (:community_id, 'paused', 50, false, 0, 0, '{}'::jsonb)
            """
        ),
        {"community_id": disabled_registry},
    )
    await db_session.commit()

    result = await compact_dev_truth_source(
        db_session,
        database_url="postgresql+asyncpg://localhost/reddit_signal_scanner_test",
        dry_run=False,
    )

    assert result.deleted_disabled_registry == 1
    assert result.deleted_inactive_runtime == 1
    assert result.deleted_inactive_category_map == 1
    assert result.deleted_inactive_cache == 1
    assert result.deleted_inactive_pool == 1
    remaining_pool_names = (
        (
            await db_session.execute(
                text("SELECT name FROM community_pool ORDER BY name")
            )
        )
        .scalars()
        .all()
    )
    assert remaining_pool_names == ["r/keep_posts"]


@pytest.mark.asyncio
async def test_compact_dev_truth_source_refuses_non_dev_database(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(RuntimeError):
        await compact_dev_truth_source(
            db_session,
            database_url="postgresql+asyncpg://localhost/reddit_signal_scanner",
            dry_run=True,
        )


@pytest.mark.asyncio
async def test_compact_dev_truth_source_refuses_unhealthy_truth_source(
    db_session: AsyncSession,
    async_truncate_test_tables,
) -> None:
    await async_truncate_test_tables(
        "community_governance_decision",
        "community_domain_membership",
        "community_runtime_state",
        "community_registry",
        "community_category_map",
        "community_cache",
        "community_pool",
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name, tier, categories, description_keywords, daily_posts,
                avg_comment_length, semantic_quality_score, priority,
                is_active, health_status, auto_tier_enabled
            )
            VALUES (
                'r/drifted_pool', 'silver', '[]'::jsonb, '{}'::jsonb,
                0, 0, 0.50, 'medium', true, 'warning', true
            )
            """
        )
    )
    await db_session.commit()

    with pytest.raises(RuntimeError, match="truth-source is unhealthy"):
        await compact_dev_truth_source(
            db_session,
            database_url="postgresql+asyncpg://localhost/reddit_signal_scanner_test",
            dry_run=False,
        )
