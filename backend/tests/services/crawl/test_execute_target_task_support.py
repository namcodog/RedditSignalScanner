from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.execute_target_task_support import (
    load_backfill_floor,
    load_community_blacklist_status,
)


async def _seed_truth_community(
    db_session: AsyncSession,
    *,
    subreddit: str,
    decision: str,
) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name, description, is_active)
            VALUES ('Tools_EDC', 'Tools_EDC', 'test seed', true)
            ON CONFLICT (key) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                description = EXCLUDED.description,
                is_active = TRUE
            """
        )
    )
    registry_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO community_registry (
                    platform, community_name, display_name, canonical_url,
                    source_of_truth, is_enabled
                )
                VALUES (
                    'reddit', :name, :display_name, :canonical_url,
                    'registry', true
                )
                RETURNING id
                """
            ),
            {
                "name": subreddit,
                "display_name": subreddit,
                "canonical_url": f"https://reddit.com/{subreddit}",
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
                    :community_id, 'Tools_EDC', 'manual', 0.900,
                    true, true, '{}'::jsonb, 'test seed'
                )
                RETURNING id
                """
            ),
            {"community_id": registry_id},
        )
    ).scalar_one()
    await db_session.execute(
        text(
            """
            INSERT INTO community_governance_decision (
                membership_id, decision, reason_code, evidence, decided_at, is_current
            )
            VALUES (
                :membership_id, :decision, 'test_seed', '{}'::jsonb, :decided_at, true
            )
            """
        ),
        {
            "membership_id": membership_id,
            "decision": decision,
            "decided_at": datetime.now(timezone.utc),
        },
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_load_community_blacklist_status_returns_true_for_blocked_truth_source(
    db_session: AsyncSession,
    reset_community_tables,
) -> None:
    await db_session.commit()
    await _seed_truth_community(
        db_session,
        subreddit="r/blocked_demo",
        decision="blocked",
    )

    blocked = await load_community_blacklist_status(
        session=db_session,
        subreddit="r/blocked_demo",
    )

    assert blocked is True


@pytest.mark.asyncio
async def test_load_community_blacklist_status_returns_false_for_approved_truth_source(
    db_session: AsyncSession,
    reset_community_tables,
) -> None:
    await db_session.commit()
    await _seed_truth_community(
        db_session,
        subreddit="r/approved_demo",
        decision="approved",
    )

    blocked = await load_community_blacklist_status(
        session=db_session,
        subreddit="r/approved_demo",
    )

    assert blocked is False


@pytest.mark.asyncio
async def test_load_community_blacklist_status_returns_none_when_truth_source_missing(
    db_session: AsyncSession,
    reset_community_tables,
) -> None:
    await db_session.commit()

    blocked = await load_community_blacklist_status(
        session=db_session,
        subreddit="r/missing_demo",
    )

    assert blocked is None


@pytest.mark.asyncio
async def test_load_backfill_floor_reads_truth_source_runtime(
    db_session: AsyncSession,
    reset_community_tables,
) -> None:
    floor = datetime(2026, 3, 1, tzinfo=timezone.utc)
    registry_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO community_registry (
                    platform, community_name, display_name, canonical_url,
                    source_of_truth, is_enabled
                )
                VALUES (
                    'reddit', 'r/floor_demo', 'r/floor_demo',
                    'https://reddit.com/r/floor_demo', 'registry', true
                )
                RETURNING id
                """
            )
        )
    ).scalar_one()
    await db_session.execute(
        text(
            """
            INSERT INTO community_runtime_state (
                community_id, crawl_status, crawl_priority, is_enabled,
                sample_posts, sample_comments, backfill_floor, runtime_notes
            )
            VALUES (
                :community_id, 'active', 50, true,
                0, 0, :backfill_floor, '{}'::jsonb
            )
            """
        ),
        {"community_id": registry_id, "backfill_floor": floor},
    )
    await db_session.commit()

    loaded = await load_backfill_floor(session=db_session, subreddit="r/floor_demo")

    assert loaded == floor
