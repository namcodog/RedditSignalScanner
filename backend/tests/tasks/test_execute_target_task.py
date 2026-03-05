from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.infrastructure.reddit_client import RedditGlobalRateLimitExceeded
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target


async def _load_task_outbox() -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, payload, status
                FROM task_outbox
                ORDER BY created_at
                """
            )
        )
        return [dict(row) for row in rows.mappings().all()]


@pytest.mark.asyncio
async def test_execute_target_reads_plan_from_crawler_run_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="cold_start",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=123),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human=idempotency_key_human,
            config=plan.model_dump(mode="json"),
        )
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {"new_posts": 1, "updated_posts": 0, "duplicates": 0}

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["crawl_run_id"] == crawl_run_id
    assert result["target_id"] == target_id
    assert result["community_run_id"] == target_id
    assert result["plan_kind"] == "backfill_posts"
    assert result["subreddit"] == subreddit

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status, metrics->>'new_posts'
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        status, new_posts = row.one()
        assert status == "completed"
        assert new_posts == "1"


@pytest.mark.asyncio
async def test_execute_target_rejects_old_backfill_plan_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_old_plan"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        version=1,
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="cold_start",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=10),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human=idempotency_key_human,
            config=plan.model_dump(mode="json"),
        )
        await session.commit()

    async def fail_execute_crawl_plan(**_: Any) -> dict[str, object]:
        raise AssertionError("execute_crawl_plan should not run for old plan version")

    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fail_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["status"] == "partial"
    assert result["reason"] == "schema_mismatch"
    assert result["plan_kind"] == "backfill_posts"

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status, error_code, metrics->>'plan_version'
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        status, error_code, plan_version = row.one()
        assert status == "partial"
        assert error_code == "schema_mismatch"
        assert plan_version == "1"


@pytest.mark.asyncio
async def test_execute_target_allows_nested_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_seed_nested"
    target_id = str(uuid.uuid4())

    plan_config = {
        "plan_kind": "seed_top_year",
        "target_type": "subreddit",
        "target_value": subreddit,
        "reason": "seed_sampling",
        "limits": {"posts_limit": 10},
        "meta": {"queue": "backfill_queue"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            config=plan_config,
        )
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**kwargs: Any) -> dict[str, object]:
        session = kwargs["session"]
        async with session.begin_nested():
            await session.execute(text("SELECT 1"))
        return {"status": "completed", "new_posts": 0}

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "completed"

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        assert row.scalar_one() == "completed"


@pytest.mark.asyncio
async def test_execute_target_skips_completed_target(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    subreddit = "r/test"

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="completed",
            config={"plan_kind": "patrol", "target_type": "subreddit", "target_value": subreddit, "reason": "cache_expired", "limits": {"posts_limit": 10}},
        )
        await session.execute(
            text(
                """
                UPDATE crawler_run_targets
                SET metrics = CAST(:metrics AS jsonb)
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id, "metrics": '{"new_posts": 99}'},
        )
        await session.commit()

    called: dict[str, bool] = {"execute": False}

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        called["execute"] = True
        return {"new_posts": 1}

    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["status"] == "skipped"
    assert result["reason"] == "already_completed"


@pytest.mark.asyncio
async def test_execute_target_skips_non_queued_status() -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    subreddit = "r/test"

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="running",
            config={
                "plan_kind": "patrol",
                "target_type": "subreddit",
                "target_value": subreddit,
                "reason": "cache_expired",
                "limits": {"posts_limit": 10},
            },
        )
        await session.commit()

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["status"] == "skipped"
    assert result["reason"] == "status_running"


@pytest.mark.asyncio
async def test_execute_target_skips_when_community_lock_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/lock_busy"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="cold_start",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=100),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human=idempotency_key_human,
            config=plan.model_dump(mode="json"),
        )
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    called = {"execute": False}

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        called["execute"] = True
        return {}

    async def fake_try_lock(*_: Any, **__: Any) -> bool:
        return False

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)
    monkeypatch.setattr(crawl_execute_task, "_try_acquire_community_lock", fake_try_lock)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["status"] == "partial"
    assert result["reason"] == "community_locked"
    assert called["execute"] is False

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status, error_code, metrics
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        status, error_code, metrics = row.one()
        assert status == "partial"
        assert error_code == "community_locked"
        assert metrics.get("lock_skipped_count") == 1
        assert metrics.get("metrics_schema_version") == 2
        assert metrics.get("stop_reason") == "community_locked"
        assert metrics.get("api_calls_total") == 0
    assert called["execute"] is False


@pytest.mark.asyncio
async def test_execute_target_skips_partial_target(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    subreddit = "r/test"

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="partial",
            config={
                "plan_kind": "patrol",
                "target_type": "subreddit",
                "target_value": subreddit,
                "reason": "cache_expired",
                "limits": {"posts_limit": 10},
            },
        )
        await session.execute(
            text(
                """
                UPDATE crawler_run_targets
                SET metrics = CAST(:metrics AS jsonb)
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id, "metrics": '{"new_posts": 3, "error": "timeout"}'},
        )
        await session.commit()

    called: dict[str, bool] = {"execute": False}

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        called["execute"] = True
        return {"new_posts": 1}

    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)

    assert result["status"] == "skipped"
    assert result["reason"] == "already_partial"
    assert called["execute"] is False


@pytest.mark.asyncio
async def test_execute_target_patrol_timeout_marks_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task
    from app.services.infrastructure import task_outbox_service

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_patrol_timeout"
    target_id = str(uuid.uuid4())

    plan_config = {
        "plan_kind": "patrol",
        "target_type": "subreddit",
        "target_value": subreddit,
        "reason": "cache_expired",
        "limits": {"posts_limit": 80},
        "meta": {"queue": "patrol_queue"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            config=plan_config,
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def slow_execute_crawl_plan(**_: Any) -> dict[str, object]:
        await asyncio.sleep(0.1)
        return {"new_posts": 0}

    monkeypatch.setenv("OUTBOX_ENV_FINGERPRINT", "test-fingerprint")
    monkeypatch.setattr(task_outbox_service, "_OUTBOX_ENV_FINGERPRINT", None)
    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", slow_execute_crawl_plan)
    monkeypatch.setattr(crawl_execute_task, "PATROL_TARGET_TIME_BUDGET_SECONDS", 0.01)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "timeout"

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT status, error_code, metrics
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        status, error_code, metrics = row.one()
        assert status == "partial"
        assert error_code == "timeout"
        assert metrics.get("metrics_schema_version") == 2
        assert metrics.get("stop_reason") == "timeout"
        assert metrics.get("api_calls_total") == 0

    # Auto compensation target should be queued (low priority) and enqueued once
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, status, config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.mappings().all()
    assert len(records) == 2
    comp = [r for r in records if str(r["id"]) != target_id][0]
    assert str(comp["status"]) == "queued"
    comp_cfg = comp["config"] if isinstance(comp["config"], dict) else {}
    comp_meta = comp_cfg.get("meta") or {}
    assert comp_meta.get("retry_of_target_id") == target_id
    assert comp_meta.get("compensation_reason") == "timeout"

    outbox_rows = await _load_task_outbox()
    assert len(outbox_rows) == 1
    payload = outbox_rows[0].get("payload") or {}
    assert payload.get("target_id") == str(comp["id"])
    assert payload.get("queue") == "compensation_queue"
    assert payload.get("env_fingerprint") == "test-fingerprint"


@pytest.mark.asyncio
async def test_execute_target_partial_outcome_generates_compensation_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_partial_outcome"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="cold_start",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=1000),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human="human",
            config=plan.model_dump(mode="json"),
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {
            "status": "partial",
            "reason": "cursor_remaining",
            "cursor_after": "t3_next",
            "new_posts": 10,
        }

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "cursor_remaining"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, status, config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.mappings().all()

    assert len(records) == 2
    original = [r for r in records if str(r["id"]) == target_id][0]
    assert str(original["status"]) == "partial"
    comp = [r for r in records if str(r["id"]) != target_id][0]
    assert str(comp["status"]) == "queued"
    comp_cfg = comp["config"] if isinstance(comp["config"], dict) else {}
    meta = comp_cfg.get("meta") or {}
    assert meta.get("retry_of_target_id") == target_id
    assert meta.get("cursor_after") == "t3_next"
    assert meta.get("compensation_reason") == "cursor_remaining"

    outbox_rows = await _load_task_outbox()
    assert len(outbox_rows) == 1
    payload = outbox_rows[0].get("payload") or {}
    assert payload.get("target_id") == str(comp["id"])
    assert payload.get("queue") == "compensation_queue"


@pytest.mark.asyncio
async def test_execute_target_partial_outcome_uses_compensation_delay_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    monkeypatch.setenv("COMPENSATION_DELAY_ENABLED", "true")
    monkeypatch.setenv("COMPENSATION_BASE_DELAY_SECONDS", "30")
    monkeypatch.setenv("COMPENSATION_MAX_DELAY_SECONDS", "300")
    monkeypatch.setenv("COMPENSATION_JITTER_SECONDS", "0")
    monkeypatch.setenv("COMPENSATION_BATCH_SIZE", "1")
    get_settings.cache_clear()

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_partial_delay"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="cold_start",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=1000),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human="human",
            config=plan.model_dump(mode="json"),
        )
        await ensure_crawler_run_target(
            session,
            community_run_id=str(uuid.uuid4()),
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key="existing",
            idempotency_key_human="existing",
            config={"meta": {"is_compensation": True}},
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {
            "status": "partial",
            "reason": "cursor_remaining",
            "cursor_after": "t3_next",
            "new_posts": 10,
        }

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "cursor_remaining"
    outbox_rows = await _load_task_outbox()
    assert len(outbox_rows) == 1
    payload = outbox_rows[0].get("payload") or {}
    assert payload.get("queue") == "compensation_queue"
    assert payload.get("countdown") == 30


@pytest.mark.asyncio
async def test_finalize_backfill_marks_capped_on_cursor_remaining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    now = datetime.now(timezone.utc)
    subreddit = "r/test_backfill_capped"
    backfill_floor = now - timedelta(days=60)

    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name=subreddit,
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.50"),
                backfill_floor=backfill_floor,
            )
        )
        await session.commit()

    async def fake_count_posts_since(*_: Any, **__: Any) -> int:
        return 2000

    async def fake_count_comments_since(*_: Any, **__: Any) -> int:
        return 50000

    monkeypatch.setattr(crawl_execute_task, "_count_posts_since", fake_count_posts_since)
    monkeypatch.setattr(
        crawl_execute_task, "_count_comments_since", fake_count_comments_since
    )

    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="bootstrap_backfill",
        window=CrawlPlanWindow(since=now - timedelta(days=7), until=now),
        limits=CrawlPlanLimits(posts_limit=1000),
        meta={"sort": "new"},
    )
    outcome = {
        "status": "partial",
        "reason": "cursor_remaining",
        "min_seen_created_at": (now - timedelta(days=1)).isoformat(),
        "cursor_after": "t3_next",
    }

    async with SessionFactory() as session:
        await crawl_execute_task._finalize_backfill_status(
            session=session,
            subreddit=subreddit,
            plan=plan,
            outcome=outcome,
        )
        await session.commit()

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT backfill_status, backfill_capped
                FROM community_cache
                WHERE community_name = :name
                """
            ),
            {"name": subreddit},
        )
        status, capped = row.one()
        assert status == "DONE_CAPPED"
        assert capped is True
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_execute_target_budget_capped_cursor_remaining_does_not_generate_compensation_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_budget_capped"

    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    until_dt = datetime.now(timezone.utc)
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="auto_backfill_after_approval",
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=100),
        meta={"sort": "new", "budget_cap": True},
    )
    idempotency_key = compute_idempotency_key(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human="human",
            config=plan.model_dump(mode="json"),
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {
            "status": "partial",
            "reason": "cursor_remaining",
            "cursor_after": "t3_next",
            "new_posts": 10,
        }

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "cursor_remaining"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, status
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.all()

    assert len(records) == 1
    assert str(records[0][0]) == target_id
    assert str(records[0][1]) == "partial"
    outbox_rows = await _load_task_outbox()
    assert outbox_rows == []


@pytest.mark.asyncio
async def test_execute_target_probe_partial_does_not_generate_compensation_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    query = "probe query"

    plan_config = {
        "plan_kind": "probe",
        "target_type": "query",
        "target_value": query,
        "reason": "user_query",
        "limits": {"posts_limit": 10},
        "meta": {"source": "search"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="r/all",
            status="queued",
            config=plan_config,
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {"status": "partial", "reason": "caps_reached"}

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "caps_reached"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, status
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.all()

    assert len(records) == 1
    assert str(records[0][0]) == target_id
    assert str(records[0][1]) == "partial"
    outbox_rows = await _load_task_outbox()
    assert outbox_rows == []


@pytest.mark.asyncio
async def test_execute_target_probe_completed_triggers_evaluator_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    monkeypatch.setenv("PROBE_AUTO_EVALUATE_ENABLED", "1")

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())

    plan_config = {
        "plan_kind": "probe",
        "target_type": "query",
        "target_value": "probe query",
        "reason": "user_query",
        "limits": {"posts_limit": 10},
        "meta": {"source": "search"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:test",
            status="queued",
            config=plan_config,
        )
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {
            "status": "completed",
            "discovered_communities_upserted": 2,
            "evidence_posts_written": 2,
        }

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)
    monkeypatch.setattr(crawl_execute_task.celery_app, "send_task", fake_send_task)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "completed"

    assert len(sent) == 1
    assert sent[0]["task_name"] == "tasks.discovery.run_community_evaluation"
    assert sent[0]["kwargs"]["queue"] == "probe_queue"


@pytest.mark.asyncio
async def test_execute_target_probe_partial_triggers_evaluator_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    monkeypatch.setenv("PROBE_AUTO_EVALUATE_ENABLED", "1")

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())

    plan_config = {
        "plan_kind": "probe",
        "target_type": "query",
        "target_value": "probe query",
        "reason": "user_query",
        "limits": {"posts_limit": 10},
        "meta": {"source": "search"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:test",
            status="queued",
            config=plan_config,
        )
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        return {"status": "partial", "reason": "caps_reached", "discovered_communities_upserted": 3}

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)
    monkeypatch.setattr(crawl_execute_task.celery_app, "send_task", fake_send_task)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "caps_reached"

    assert len(sent) == 1
    assert sent[0]["task_name"] == "tasks.discovery.run_community_evaluation"
    assert sent[0]["kwargs"]["queue"] == "probe_queue"


@pytest.mark.asyncio
async def test_execute_target_budget_exhausted_marks_partial_and_schedules_compensation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawl_execute_task

    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test_budget_exhausted"
    target_id = str(uuid.uuid4())

    plan_config = {
        "plan_kind": "patrol",
        "target_type": "subreddit",
        "target_value": subreddit,
        "reason": "cache_expired",
        "limits": {"posts_limit": 80},
        "meta": {"queue": "patrol_queue"},
    }

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            status="queued",
            config=plan_config,
        )
        await session.execute(text("DELETE FROM task_outbox"))
        await session.commit()

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    async def fake_execute_crawl_plan(**_: Any) -> dict[str, object]:
        raise RedditGlobalRateLimitExceeded(wait_seconds=30)

    monkeypatch.setattr(crawl_execute_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(crawl_execute_task, "execute_crawl_plan", fake_execute_crawl_plan)

    result = await crawl_execute_task._execute_target_impl(target_id=target_id)
    assert result["status"] == "partial"
    assert result["reason"] == "budget_exhausted"

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, status, error_code
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                ORDER BY started_at
                """
            ),
            {"rid": crawl_run_id},
        )
        records = rows.all()
    assert len(records) == 2
    assert records[0][1] == "partial"
    assert records[0][2] == "budget_exhausted"
    assert records[1][1] == "queued"

    outbox_rows = await _load_task_outbox()
    assert len(outbox_rows) == 1
    payload = outbox_rows[0].get("payload") or {}
    assert payload.get("queue") == "compensation_queue"
    assert payload.get("countdown") == 30
