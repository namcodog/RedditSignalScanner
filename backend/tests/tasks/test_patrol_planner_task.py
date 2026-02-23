from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


@pytest.mark.asyncio
async def test_patrol_heartbeat_planner_writes_queued_targets_and_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import crawler_task

    # Guard: planner should not build a Reddit client (execution is delegated to execute_target).
    async def _boom(*_: Any, **__: Any) -> Any:
        raise AssertionError("planner must not call _build_reddit_client")

    monkeypatch.setattr(crawler_task, "_build_reddit_client", _boom)

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    now = datetime.now(timezone.utc)
    active = "r/test_patrol_active"
    blocked = "r/test_patrol_blocked"

    async with SessionFactory() as session:
        session.add(
            CommunityPool(
                name=active,
                tier="high",
                priority="high",
                categories=[],
                description_keywords={},
                daily_posts=10,
                avg_comment_length=0,
                quality_score=0.6,
                user_feedback_count=0,
                discovered_count=0,
                is_active=True,
                is_blacklisted=False,
                blacklist_reason=None,
                health_status="healthy",
                auto_tier_enabled=False,
            )
        )
        session.add(
            CommunityPool(
                name=blocked,
                tier="high",
                priority="high",
                categories=[],
                description_keywords={},
                daily_posts=10,
                avg_comment_length=0,
                quality_score=0.6,
                user_feedback_count=0,
                discovered_count=0,
                is_active=True,
                is_blacklisted=True,
                blacklist_reason="blocked",
                health_status="critical",
                auto_tier_enabled=False,
            )
        )
        await session.commit()

    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name=active,
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
                last_seen_post_id="p123",
                last_seen_created_at=now - timedelta(hours=2),
                backfill_floor=now - timedelta(days=90),
                last_attempt_at=None,
                member_count=None,
                total_posts_fetched=0,
                dedup_rate=None,
            )
        )
        await session.commit()

    outcome = await crawler_task._crawl_seeds_incremental_impl(force_refresh=False)
    crawl_run_id = str(outcome.get("run_id") or "")
    assert crawl_run_id, "planner should return crawl_run_id"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, subreddit, status, plan_kind, idempotency_key, config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY subreddit
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.mappings().all()

    assert [r["subreddit"] for r in records] == [active]
    record = records[0]
    assert str(record["status"]) == "queued"
    assert str(record["plan_kind"]) == "patrol"
    assert str(record["idempotency_key"])

    config = record["config"] if isinstance(record["config"], dict) else {}
    assert config.get("plan_kind") == "patrol"
    assert config.get("target_value") == active
    meta = config.get("meta") or {}
    assert meta.get("cursor_last_seen_post_id") == "p123"
    assert "cursor_backfill_floor" not in meta

    # Enqueue once to patrol_queue
    assert len(sent) == 1
    assert sent[0]["task_name"] == "tasks.crawler.execute_target"
    assert sent[0]["kwargs"]["kwargs"]["target_id"] == str(record["id"])
    assert sent[0]["kwargs"]["queue"] == "patrol_queue"

    # Planner must not mutate backfill_floor
    async with SessionFactory() as session:
        cache = await session.execute(
            select(CommunityCache.backfill_floor).where(CommunityCache.community_name == active)
        )
        (backfill_floor,) = cache.one()
        assert backfill_floor is not None


@pytest.mark.asyncio
async def test_patrol_planner_idempotent_enqueue_with_same_crawl_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import crawler_task
    from app.services.community_pool_loader import CommunityProfile

    sent: list[str] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append(task_name)

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    crawl_run_id = str(uuid.uuid4())
    profiles = [
        CommunityProfile(
            name="r/test_patrol_idempotent",
            tier="high",
            categories=[],
            description_keywords={},
            daily_posts=10,
            avg_comment_length=0,
            quality_score=0.6,
            priority="high",
        )
    ]

    inserted_first = await crawler_task._plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=False,
    )
    inserted_second = await crawler_task._plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=False,
    )

    assert inserted_first["inserted"] == 1
    assert inserted_second["inserted"] == 0
    assert sent.count("tasks.crawler.execute_target") == 1


@pytest.mark.asyncio
async def test_patrol_planner_clamps_posts_limit_and_sets_guardrails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task
    from app.services.community_pool_loader import CommunityProfile

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    class DummyTier:
        post_limit = 10_000
        time_filter = "all"
        hot_cache_ttl_hours = 999_999

        def pick_sort(self, *, default_sort: str) -> str:
            return default_sort

    monkeypatch.setattr(crawler_task, "_tier_settings_for", lambda *_: DummyTier())

    crawl_run_id = str(uuid.uuid4())
    profiles = [
        CommunityProfile(
            name="r/test_patrol_guardrails",
            tier="high",
            categories=[],
            description_keywords={},
            daily_posts=10,
            avg_comment_length=0,
            quality_score=0.6,
            priority="high",
        )
    ]

    outcome = await crawler_task._plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=False,
    )
    assert outcome["inserted"] == 1
    assert outcome["enqueued"] == 1

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
    assert meta.get("patrol_comments_enabled") is False

    assert sent[0]["task_name"] == "tasks.crawler.execute_target"
    assert sent[0]["kwargs"]["queue"] == "patrol_queue"


@pytest.mark.asyncio
async def test_patrol_planner_limits_total_targets_per_heartbeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task
    from app.services.community_pool_loader import CommunityProfile

    monkeypatch.setattr(crawler_task, "EFFECTIVE_BATCH_SIZE", 2)

    sent: list[str] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append(task_name)

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    crawl_run_id = str(uuid.uuid4())
    profiles = [
        CommunityProfile(
            name=f"r/test_patrol_limit_{idx}",
            tier="high",
            categories=[],
            description_keywords={},
            daily_posts=10,
            avg_comment_length=0,
            quality_score=0.6,
            priority="high",
        )
        for idx in range(3)
    ]

    outcome = await crawler_task._plan_patrol_targets(
        crawl_run_id=crawl_run_id,
        profiles=profiles,
        force_refresh=False,
    )

    assert outcome["inserted"] == 2
    assert outcome["enqueued"] == 2
    assert sent.count("tasks.crawler.execute_target") == 2


@pytest.mark.asyncio
async def test_patrol_planner_triggers_probe_hot_fallback_when_due_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    monkeypatch.setenv("PROBE_HOT_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_MIN_DUE", "3")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_COOLDOWN_MINUTES", "120")

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    now = datetime.now(timezone.utc)
    active = "r/test_patrol_probe_fallback"

    async with SessionFactory() as session:
        session.add(
            CommunityPool(
                name=active,
                tier="high",
                priority="high",
                categories=[],
                description_keywords={},
                daily_posts=10,
                avg_comment_length=0,
                quality_score=0.6,
                user_feedback_count=0,
                discovered_count=0,
                is_active=True,
                is_blacklisted=False,
                blacklist_reason=None,
                health_status="healthy",
                auto_tier_enabled=False,
            )
        )
        await session.commit()

    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name=active,
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
                last_seen_post_id="p-probe-1",
                last_seen_created_at=now - timedelta(hours=2),
                backfill_floor=now - timedelta(days=90),
                last_attempt_at=None,
                member_count=None,
                total_posts_fetched=0,
                dedup_rate=None,
            )
        )
        await session.commit()

    await crawler_task._crawl_seeds_incremental_impl(force_refresh=False)

    probe_calls = [
        call for call in sent if call["task_name"] == "tasks.probe.run_hot_probe"
    ]
    assert len(probe_calls) == 1
    assert probe_calls[0]["kwargs"]["queue"] == "probe_queue"


@pytest.mark.asyncio
async def test_patrol_planner_skips_probe_hot_fallback_when_recent_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    monkeypatch.setenv("PROBE_HOT_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_MIN_DUE", "3")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_COOLDOWN_MINUTES", "180")

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)

    now = datetime.now(timezone.utc)
    active = "r/test_patrol_probe_recent"

    async with SessionFactory() as session:
        session.add(
            CommunityPool(
                name=active,
                tier="high",
                priority="high",
                categories=[],
                description_keywords={},
                daily_posts=10,
                avg_comment_length=0,
                quality_score=0.6,
                user_feedback_count=0,
                discovered_count=0,
                is_active=True,
                is_blacklisted=False,
                blacklist_reason=None,
                health_status="healthy",
                auto_tier_enabled=False,
            )
        )
        await session.commit()

    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name=active,
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
                last_seen_post_id="p-probe-2",
                last_seen_created_at=now - timedelta(hours=2),
                backfill_floor=now - timedelta(days=90),
                last_attempt_at=None,
                member_count=None,
                total_posts_fetched=0,
                dedup_rate=None,
            )
        )
        await session.commit()

    recent_probe_config = {
        "plan_kind": "probe",
        "meta": {"source": "hot"},
    }
    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                INSERT INTO crawler_run_targets (
                    id, crawl_run_id, subreddit, status, config, metrics, started_at
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:crawl_run_id AS uuid),
                    :subreddit,
                    'queued',
                    CAST(:config AS jsonb),
                    '{}'::jsonb,
                    :started_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "crawl_run_id": str(uuid.uuid4()),
                "subreddit": "r/probe_hot_recent",
                "config": json.dumps(recent_probe_config),
                "started_at": now - timedelta(minutes=10),
            },
        )
        await session.commit()

    await crawler_task._crawl_seeds_incremental_impl(force_refresh=False)

    probe_calls = [
        call for call in sent if call["task_name"] == "tasks.probe.run_hot_probe"
    ]
    assert probe_calls == []
