from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import text

import app.services.crawl.target_planner as target_planner
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.community_pool_loader import CommunityProfile
from app.services.crawl.crawler_runs_service import ensure_crawler_run


async def _commit_session(session: Any, *, context: str) -> bool:
    del context
    await session.commit()
    return True


@pytest.mark.asyncio
async def test_queue_planned_crawl_targets_is_idempotent_for_same_run() -> None:
    crawl_run_id = str(uuid.uuid4())
    subreddit = f"r/test_planned_target_{uuid.uuid4().hex[:8]}"

    async with SessionFactory() as session:
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "test_queue_planned_crawl_targets"},
        )
        await session.commit()

    enqueued: list[tuple[str, str]] = []

    async def fake_enqueue(
        *,
        session: Any,
        target_id: str,
        queue: str,
        countdown: int | None = None,
    ) -> bool:
        del session, countdown
        enqueued.append((target_id, queue))
        return True

    deps = target_planner.QueuePlannedTargetsDeps(
        session_factory=SessionFactory,
        enqueue_target_outbox=fake_enqueue,
        commit_session=_commit_session,
    )
    target = target_planner.build_patrol_target(
        subreddit=subreddit,
        reason="cache_expired",
        posts_limit=25,
        time_filter="day",
        sort="hot",
        hot_cache_ttl_hours=24,
        extra_meta={"tier": "high", "patrol_comments_enabled": False},
    )

    first = await target_planner.queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=[target],
        deps=deps,
        commit_context="test_queue_planned_crawl_targets:first",
    )
    second = await target_planner.queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=[target],
        deps=deps,
        commit_context="test_queue_planned_crawl_targets:second",
    )

    assert first.inserted == 1
    assert first.enqueued == 1
    assert second.inserted == 0
    assert second.enqueued == 0
    assert len(enqueued) == 1
    assert enqueued[0][1] == "patrol_queue"


@pytest.mark.asyncio
async def test_plan_patrol_targets_applies_guardrails_and_uses_waterline() -> None:
    crawl_run_id = str(uuid.uuid4())
    subreddit = f"r/test_patrol_service_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    async with SessionFactory() as session:
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "test_plan_patrol_targets"},
        )
        session.add(
            CommunityPool(
                name=subreddit,
                tier="high",
                categories={"topic": ["test"]},
                description_keywords={"test": 1},
                daily_posts=10,
                quality_score=0.6,
                priority="high",
            )
        )
        await session.flush()
        session.add(
            CommunityCache(
                community_name=subreddit,
                last_crawled_at=now - timedelta(days=1),
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=0.5,
                hit_count=0,
                crawl_priority=50,
                crawl_frequency_hours=1,
                is_active=True,
                empty_hit=0,
                success_hit=0,
                failure_hit=0,
                avg_valid_posts=0,
                quality_tier="medium",
                last_seen_post_id="p-waterline",
                last_seen_created_at=now - timedelta(hours=2),
                backfill_floor=now - timedelta(days=30),
                last_attempt_at=None,
                member_count=None,
                total_posts_fetched=0,
                dedup_rate=None,
            )
        )
        await session.commit()

    enqueued: list[tuple[str, str]] = []

    async def fake_enqueue(
        *,
        session: Any,
        target_id: str,
        queue: str,
        countdown: int | None = None,
    ) -> bool:
        del session, countdown
        enqueued.append((target_id, queue))
        return True

    class DummyTier:
        post_limit = 10_000
        time_filter = "all"
        hot_cache_ttl_hours = 999_999

        def pick_sort(self, *, default_sort: str) -> str:
            return default_sort

    deps = target_planner.PatrolTargetPlannerDeps(
        session_factory=SessionFactory,
        tier_settings_for=lambda *_: DummyTier(),
        queue_deps=target_planner.QueuePlannedTargetsDeps(
            session_factory=SessionFactory,
            enqueue_target_outbox=fake_enqueue,
            commit_session=_commit_session,
        ),
        patrol_default_posts_limit=80,
        patrol_max_posts_limit=100,
        effective_batch_size=10,
        effective_time_filter="month",
        effective_sort="top",
        effective_hot_cache_ttl_hours=72,
    )

    outcome = await target_planner.plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=[
            CommunityProfile(
                name=subreddit,
                tier="high",
                categories=[],
                description_keywords={},
                daily_posts=10,
                avg_comment_length=0,
                quality_score=0.6,
                priority="high",
            )
        ],
        force_refresh=False,
        deps=deps,
    )

    assert outcome.inserted == 1
    assert outcome.enqueued == 1
    assert len(enqueued) == 1
    assert enqueued[0][1] == "patrol_queue"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                LIMIT 1
                """
            ),
            {"rid": crawl_run_id},
        )
        record = rows.mappings().first()

    assert record is not None
    config = record["config"] if isinstance(record["config"], dict) else {}
    assert (config.get("limits") or {}).get("posts_limit") == 100
    meta = config.get("meta") or {}
    assert meta.get("time_filter") in {"hour", "day"}
    assert meta.get("cursor_last_seen_post_id") == "p-waterline"
    assert meta.get("patrol_comments_enabled") is False
