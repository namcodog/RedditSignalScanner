from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity


@pytest.mark.asyncio
async def test_candidate_vetting_plans_and_enqueues_backfill_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Key 口径（第4）：candidate 先验毒回填 30 天（budget_cap），回填完成后才评估。

    本测试只验证“验毒回填 targets 能自动下单 + 幂等不重复下单”。
    """
    from app.services.discovery import candidate_vetting_service

    sent: list[dict[str, Any]] = []

    async def fake_enqueue_execute_target_outbox(
        *_: Any, target_id: str, queue: str, **__: Any
    ) -> bool:
        sent.append({"target_id": target_id, "queue": queue})
        return True

    monkeypatch.setattr(
        candidate_vetting_service,
        "enqueue_execute_target_outbox",
        fake_enqueue_execute_target_outbox,
    )

    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/test_vetting'"))
        await session.execute(text("DELETE FROM community_pool WHERE name = 'r/test_vetting'"))
        await session.commit()
        session.add(
            CommunityPool(
                name="r/test_vetting",
                tier="candidate",
                categories={},
                description_keywords={},
                is_active=True,
            )
        )
        session.add(
            DiscoveredCommunity(
                name="r/test_vetting",
                discovered_from_keywords={},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                metrics={},
                tags=[],
            )
        )
        await session.commit()

        targets1 = await candidate_vetting_service.ensure_candidate_vetting_backfill(
            session=session,
            community="r/test_vetting",
            trigger="unit_test",
            days=30,
            slice_days=7,
            total_posts_budget=300,
        )
        await session.commit()

        assert isinstance(targets1, list)
        assert targets1  # should create at least 1 slice target
        assert all(isinstance(t, str) for t in targets1)
        assert all(len(t) >= 8 for t in targets1)

        # idempotency: calling again should not enqueue duplicate targets
        sent_before = len(sent)
        targets2 = await candidate_vetting_service.ensure_candidate_vetting_backfill(
            session=session,
            community="r/test_vetting",
            trigger="unit_test",
            days=30,
            slice_days=7,
            total_posts_budget=300,
        )
        await session.commit()
        assert targets2 == []
        assert len(sent) == sent_before

    assert sent
    assert all(s["queue"] == "backfill_posts_queue_v2" for s in sent)

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                "SELECT metrics FROM discovered_communities WHERE name = :name",
            ),
            {"name": "r/test_vetting"},
        )
        metrics = row.scalar_one()
        assert isinstance(metrics, dict)
        vetting = metrics.get("vetting") or {}
        assert vetting.get("status") in {"queued", "running", "completed"}
        assert vetting.get("days") == 30
        assert vetting.get("slice_days") == 7
        assert vetting.get("total_posts_budget") == 300
        assert isinstance(vetting.get("crawl_run_id"), str)


@pytest.mark.asyncio
async def test_candidate_vetting_completion_triggers_single_community_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    当某社区的验毒回填 targets 全部 completed/partial（budget_cap 允许 partial）后，
    系统应 best-effort 触发“单社区评估”任务，而不是立刻扫全表。
    """
    from app.services.discovery import candidate_vetting_service

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    monkeypatch.setattr(candidate_vetting_service.celery_app, "send_task", fake_send_task)

    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/test_vetting_done'"))
        await session.execute(text("DELETE FROM community_pool WHERE name = 'r/test_vetting_done'"))
        await session.commit()
        session.add(
            CommunityPool(
                name="r/test_vetting_done",
                tier="candidate",
                categories={},
                description_keywords={},
                is_active=True,
            )
        )
        session.add(
            DiscoveredCommunity(
                name="r/test_vetting_done",
                discovered_from_keywords={},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                metrics={},
                tags=[],
            )
        )
        await session.commit()

        target_ids = await candidate_vetting_service.ensure_candidate_vetting_backfill(
            session=session,
            community="r/test_vetting_done",
            trigger="unit_test",
            days=30,
            slice_days=7,
            total_posts_budget=300,
        )
        await session.commit()
        assert target_ids

        # Mark all vetting targets as completed (simulate backfill done)
        for tid in target_ids:
            await session.execute(
                text(
                    "UPDATE crawler_run_targets SET status='completed', completed_at=NOW() WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(uuid.UUID(tid))},
            )
        await session.commit()

        did = await candidate_vetting_service.check_vetting_and_trigger_evaluation(
            session=session, community="r/test_vetting_done"
        )
        await session.commit()

        assert did is True

    assert any(s["task_name"] == "tasks.discovery.evaluate_community" for s in sent)


@pytest.mark.asyncio
async def test_candidate_vetting_blacklisted_records_blocked_status() -> None:
    from app.services.discovery import candidate_vetting_service

    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/test_vetting_blocked'"))
        await session.execute(text("DELETE FROM community_pool WHERE name = 'r/test_vetting_blocked'"))
        await session.commit()
        session.add(
            CommunityPool(
                name="r/test_vetting_blocked",
                tier="candidate",
                categories={},
                description_keywords={},
                is_active=True,
                is_blacklisted=True,
            )
        )
        session.add(
            DiscoveredCommunity(
                name="r/test_vetting_blocked",
                discovered_from_keywords={},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                metrics={},
                tags=[],
            )
        )
        await session.commit()

        target_ids = await candidate_vetting_service.ensure_candidate_vetting_backfill(
            session=session,
            community="r/test_vetting_blocked",
            trigger="unit_test",
        )
        await session.commit()

        assert target_ids == []

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                "SELECT metrics FROM discovered_communities WHERE name = :name",
            ),
            {"name": "r/test_vetting_blocked"},
        )
        metrics = row.scalar_one()
        assert isinstance(metrics, dict)
        vetting = metrics.get("vetting") or {}
        assert vetting.get("status") == "blocked"
        assert vetting.get("reason") == "community_pool_blacklisted"


@pytest.mark.asyncio
async def test_candidate_vetting_completion_records_trigger_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.discovery import candidate_vetting_service

    def fake_send_task(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("broker down")

    monkeypatch.setattr(candidate_vetting_service.celery_app, "send_task", fake_send_task)

    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/test_vetting_trigger_fail'"))
        await session.execute(text("DELETE FROM community_pool WHERE name = 'r/test_vetting_trigger_fail'"))
        await session.commit()
        session.add(
            CommunityPool(
                name="r/test_vetting_trigger_fail",
                tier="candidate",
                categories={},
                description_keywords={},
                is_active=True,
            )
        )
        session.add(
            DiscoveredCommunity(
                name="r/test_vetting_trigger_fail",
                discovered_from_keywords={},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                metrics={},
                tags=[],
            )
        )
        await session.commit()

        target_ids = await candidate_vetting_service.ensure_candidate_vetting_backfill(
            session=session,
            community="r/test_vetting_trigger_fail",
            trigger="unit_test",
        )
        await session.commit()
        assert target_ids

        for tid in target_ids:
            await session.execute(
                text(
                    "UPDATE crawler_run_targets SET status='completed', completed_at=NOW() WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(uuid.UUID(tid))},
            )
        await session.commit()

        did = await candidate_vetting_service.check_vetting_and_trigger_evaluation(
            session=session,
            community="r/test_vetting_trigger_fail",
        )
        await session.commit()

        assert did is True

    async with SessionFactory() as session:
        row = await session.execute(
            text("SELECT metrics FROM discovered_communities WHERE name = :name"),
            {"name": "r/test_vetting_trigger_fail"},
        )
        metrics = row.scalar_one()
        vetting = (metrics or {}).get("vetting") or {}
        assert vetting.get("status") == "completed"
        assert vetting.get("evaluation_trigger") == "failed"
        assert vetting.get("evaluation_trigger_error") == "broker down"
