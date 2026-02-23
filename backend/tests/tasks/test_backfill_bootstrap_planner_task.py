from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


@pytest.mark.asyncio
async def test_backfill_bootstrap_planner_enqueues_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    now = datetime.now(timezone.utc)
    community_needs = "r/backfill_needs"
    community_done = "r/backfill_done"

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(text("DELETE FROM task_outbox"))
        session.add_all(
            [
                CommunityPool(
                    name=community_needs,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
                CommunityPool(
                    name=community_done,
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
                    community_name=community_needs,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_cursor="t3_cursor",
                ),
                CommunityCache(
                    community_name=community_done,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="DONE_12M",
                ),
            ]
        )
        await session.commit()
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_MAX_TARGETS", "5")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_POSTS_LIMIT", "123")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_WINDOW_DAYS", "365")
    monkeypatch.setenv("BACKFILL_BOOTSTRAP_COOLDOWN_MINUTES", "0")

    result = await crawler_task._plan_backfill_bootstrap_impl()

    assert result["inserted"] == 1
    assert result["enqueued"] == 1

    async with SessionFactory() as session:
        outbox_row = await session.execute(
            text(
                """
                SELECT payload
                FROM task_outbox
                WHERE event_type = 'execute_target'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        )
        payload = outbox_row.scalar_one()
        row = await session.execute(
            text(
                """
                SELECT config
                FROM crawler_run_targets
                WHERE subreddit = :subreddit
                """
            ),
            {"subreddit": community_needs},
        )
        cfg = row.scalar_one()
        plan = cfg if isinstance(cfg, dict) else {}
        assert plan.get("plan_kind") == "backfill_posts"
        assert plan.get("limits", {}).get("posts_limit") == 123
        assert plan.get("meta", {}).get("cursor_after") == "t3_cursor"
        payload_dict = payload if isinstance(payload, dict) else {}
        assert payload_dict.get("queue") == "backfill_queue"


@pytest.mark.asyncio
async def test_backfill_bootstrap_planner_skips_when_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    @asynccontextmanager
    async def fake_lock(_key: str):
        yield False

    monkeypatch.setattr(crawler_task, "_planner_lock", fake_lock)

    result = await crawler_task._plan_backfill_bootstrap_impl()

    assert result["status"] == "locked"
    assert result["inserted"] == 0
    assert result["enqueued"] == 0
