from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.crawl.crawler_runs_service import ensure_crawler_run


@pytest.mark.asyncio
async def test_auto_backfill_service_creates_time_sliced_backfill_targets() -> None:
    from app.services.discovery.auto_backfill_service import plan_auto_backfill_posts_targets

    crawl_run_id = str(uuid.uuid4())
    now = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc)

    async with SessionFactory() as session:
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "test_auto_backfill"},
        )
        target_ids = await plan_auto_backfill_posts_targets(
            session=session,
            crawl_run_id=crawl_run_id,
            communities=["r/test_auto_backfill"],
            now=now,
            days=30,
            slice_days=7,
            total_posts_budget=300,
            reason="auto_backfill_after_approval",
        )
        await session.commit()

    assert len(target_ids) == 5

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        configs = [row[0] for row in rows.all()]

    assert len(configs) == 5
    for cfg in configs:
        assert isinstance(cfg, dict)
        assert cfg.get("plan_kind") == "backfill_posts"
        assert cfg.get("target_value") == "r/test_auto_backfill"
        meta = cfg.get("meta") or {}
        assert meta.get("budget_cap") is True
        assert meta.get("auto_backfill_days") == 30
        assert meta.get("auto_backfill_total_posts_budget") == 300
        limits = cfg.get("limits") or {}
        assert 1 <= int(limits.get("posts_limit") or 0) <= 300


@pytest.mark.asyncio
async def test_auto_backfill_service_skips_blacklisted_communities() -> None:
    from app.services.discovery.auto_backfill_service import plan_auto_backfill_posts_targets

    crawl_run_id = str(uuid.uuid4())
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                DELETE FROM community_pool
                WHERE name IN ('r/ab_ok', 'r/ab_black')
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO community_pool (
                    name, tier, categories, description_keywords, semantic_quality_score,
                    is_active, is_blacklisted, created_at, updated_at
                )
                VALUES
                    ('r/ab_ok', 'candidate', '{}'::jsonb, '{}'::jsonb, 0.5, true, false, :ts, :ts),
                    ('r/ab_black', 'candidate', '{}'::jsonb, '{}'::jsonb, 0.5, true, true, :ts, :ts)
                """
            ),
            {"ts": now},
        )
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id, config={"mode": "test"})
        target_ids = await plan_auto_backfill_posts_targets(
            session=session,
            crawl_run_id=crawl_run_id,
            communities=["r/ab_ok", "r/ab_black"],
            now=now,
            days=30,
            slice_days=7,
            total_posts_budget=300,
            reason="auto_backfill_after_approval",
        )
        await session.commit()

    # Only the non-blacklisted community should get targets (30d sliced into 5).
    assert len(target_ids) == 5

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT DISTINCT subreddit
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                """
            ),
            {"rid": crawl_run_id},
        )
        subs = {str(r[0]) for r in rows.all() if r and r[0]}

    assert subs == {"r/ab_ok"}
