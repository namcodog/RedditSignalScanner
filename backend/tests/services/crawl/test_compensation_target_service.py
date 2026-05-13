from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text

import app.services.crawl.compensation_target_service as compensation_service
import app.services.crawl.crawler_run_targets_service as run_targets_service
import app.services.crawl.crawler_runs_service as runs_service
import app.services.crawl.plan_contract as plan_contract
import app.services.infrastructure.task_outbox_service as outbox_service
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


def _settings(
    *, delay_enabled: bool, base_delay: int, batch_size: int
) -> SimpleNamespace:
    return SimpleNamespace(
        compensation_delay_enabled=delay_enabled,
        compensation_base_delay_seconds=base_delay,
        compensation_max_delay_seconds=300,
        compensation_jitter_seconds=0,
        compensation_batch_size=batch_size,
    )


def _deps(
    *, delay_enabled: bool = False, base_delay: int = 10, batch_size: int = 1
) -> compensation_service.CompensationTargetDeps:
    return compensation_service.CompensationTargetDeps(
        settings_factory=lambda: _settings(
            delay_enabled=delay_enabled,
            base_delay=base_delay,
            batch_size=batch_size,
        ),
        ensure_dict=lambda value: value if isinstance(value, dict) else {},
        ensure_crawler_run_target=run_targets_service.ensure_crawler_run_target,
        enqueue_target_outbox=outbox_service.enqueue_execute_target_outbox,
        compensation_queue="compensation_queue",
        backfill_posts_queue="backfill_posts_queue_v2",
        random_int=lambda _a, _b: 0,
    )


async def _reset_tables() -> None:
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(text("DELETE FROM community_cache"))
        await session.commit()


@pytest.mark.asyncio
async def test_enqueue_compensation_target_creates_backfill_target_and_outbox() -> None:
    await _reset_tables()

    now = datetime.now(timezone.utc)
    subreddit = f"r/comp_backfill_{uuid.uuid4().hex[:8]}"
    crawl_run_id = str(uuid.uuid4())

    async with SessionFactory() as session:
        session.add(
            CommunityPool(
                name=subreddit,
                tier="high",
                categories={},
                description_keywords={},
                is_active=True,
                is_blacklisted=False,
            )
        )
        await session.flush()
        session.add(
            CommunityCache(
                community_name=subreddit,
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.50"),
                is_active=True,
            )
        )
        await runs_service.ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await session.commit()

    plan = plan_contract.CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=subreddit,
        reason="bootstrap_backfill",
        window=plan_contract.CrawlPlanWindow(
            since=now,
            until=now + timedelta(seconds=1),
        ),
        limits=plan_contract.CrawlPlanLimits(posts_limit=100),
        meta={"queue": "backfill_posts_queue_v2"},
    )

    async with SessionFactory() as session:
        comp_target_id = await compensation_service.enqueue_compensation_target(
            session=session,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            original_target_id="orig-1",
            plan=plan,
            base_idempotency_key="seed-key",
            reason="timeout",
            deps=_deps(),
        )
        await session.commit()

    assert comp_target_id is not None

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT config
                FROM crawler_run_targets
                WHERE id = CAST(:target_id AS uuid)
                """
            ),
            {"target_id": comp_target_id},
        )
        payload = row.scalar_one()
        outbox = await session.execute(
            text(
                """
                SELECT payload
                FROM task_outbox
                WHERE payload->>'target_id' = :target_id
                """
            ),
            {"target_id": comp_target_id},
        )
        outbox_payload = outbox.scalar_one()

    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    assert meta.get("is_compensation") is True
    assert meta.get("retry_of_target_id") == "orig-1"
    assert meta.get("compensation_reason") == "timeout"
    assert outbox_payload.get("queue") == "backfill_posts_queue_v2"


@pytest.mark.asyncio
async def test_enqueue_compensation_target_applies_computed_delay_for_later_batches() -> None:
    await _reset_tables()

    subreddit = f"r/comp_delay_{uuid.uuid4().hex[:8]}"
    crawl_run_id = str(uuid.uuid4())
    plan = plan_contract.CrawlPlanContract(
        plan_kind="patrol",
        target_type="subreddit",
        target_value=subreddit,
        reason="low_quality_refresh",
        limits=plan_contract.CrawlPlanLimits(posts_limit=50),
        meta={"queue": "patrol_queue"},
    )

    async with SessionFactory() as session:
        await runs_service.ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        first_target = await compensation_service.enqueue_compensation_target(
            session=session,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            original_target_id="orig-1",
            plan=plan,
            base_idempotency_key="seed-key",
            reason="timeout",
            deps=_deps(delay_enabled=True, base_delay=10, batch_size=1),
        )
        second_target = await compensation_service.enqueue_compensation_target(
            session=session,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            original_target_id="orig-2",
            plan=plan,
            base_idempotency_key="seed-key-2",
            reason="budget_exhausted",
            deps=_deps(delay_enabled=True, base_delay=10, batch_size=1),
        )
        await session.commit()

    assert first_target is not None
    assert second_target is not None

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT payload
                FROM task_outbox
                WHERE payload->>'target_id' = :first_id
                   OR payload->>'target_id' = :second_id
                """
            ),
            {"first_id": first_target, "second_id": second_target},
        )
        payloads = {str((row[0] or {}).get("target_id")): row[0] for row in rows.all()}

    assert payloads[first_target].get("countdown") is None
    assert payloads[second_target].get("countdown") == 10
