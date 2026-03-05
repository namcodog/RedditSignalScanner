from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target


@pytest.mark.asyncio
async def test_seed_sampling_planner_enqueues_capped_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    now = datetime.now(timezone.utc)
    needs_seed = "r/seed_needed"
    recent_seed = "r/seed_recent"

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(text("DELETE FROM task_outbox"))
        session.add_all(
            [
                CommunityPool(
                    name=needs_seed,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
                CommunityPool(
                    name=recent_seed,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
            ]
        )
        session.add_all(
            [
                CommunityCache(
                    community_name=needs_seed,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_capped=True,
                    sample_posts=200,
                ),
                CommunityCache(
                    community_name=recent_seed,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_capped=True,
                    sample_posts=200,
                ),
            ]
        )
        await session.commit()

    recent_run_id = str(uuid.uuid4())
    recent_target_id = str(uuid.uuid4())
    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=recent_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=recent_target_id,
            crawl_run_id=recent_run_id,
            subreddit=recent_seed,
            status="completed",
            plan_kind="seed_top_year",
            idempotency_key="seed_recent",
            idempotency_key_human="seed_recent",
            config={"plan_kind": "seed_top_year"},
        )
        await session.commit()

    monkeypatch.setenv("SEED_SAMPLING_COOLDOWN_DAYS", "30")
    monkeypatch.setenv("SEED_SAMPLING_MAX_TARGETS", "10")
    monkeypatch.setenv("SEED_SAMPLING_POSTS_LIMIT", "200")
    monkeypatch.setenv("SEED_SAMPLING_MIN_POSTS", "200")

    result = await crawler_task._plan_seed_sampling_impl()

    assert result["inserted"] == 2
    assert result["enqueued"] == 2

    async with SessionFactory() as session:
        outbox_count = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM task_outbox
                WHERE event_type = 'execute_target'
                """
            )
        )
        assert int(outbox_count.scalar() or 0) == 2
        row = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM crawler_run_targets
                WHERE subreddit = :subreddit
                  AND plan_kind IN ('seed_top_year', 'seed_top_all')
                """
            ),
            {"subreddit": needs_seed},
        )
        assert int(row.scalar() or 0) == 2


@pytest.mark.asyncio
async def test_seed_sampling_planner_skips_when_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    @asynccontextmanager
    async def fake_lock(_key: str):
        yield False

    monkeypatch.setattr(crawler_task, "_planner_lock", fake_lock)

    result = await crawler_task._plan_seed_sampling_impl()

    assert result["status"] == "locked"
    assert result["inserted"] == 0
    assert result["enqueued"] == 0
