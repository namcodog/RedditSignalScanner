from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.task import TaskSummary
from app.services.analysis import analysis_remediation_support as remediation_module


class _StubSession:
    async def commit(self) -> None:
        return None


class _StubSessionFactory:
    async def __aenter__(self) -> _StubSession:
        return _StubSession()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_schedule_backfill_prefers_open_topic_route_seed_communities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REMEDIATION_BUDGET_ENABLED", "0")
    monkeypatch.setattr(remediation_module, "SessionFactory", _StubSessionFactory)

    planned: dict[str, object] = {}

    async def fake_plan_auto_backfill_posts_targets(
        *,
        session,
        crawl_run_id,
        communities,
        now,
        days,
        slice_days,
        total_posts_budget,
        reason,
        max_targets,
    ) -> list[str]:
        planned["communities"] = list(communities)
        return ["00000000-0000-0000-0000-000000000001"]

    async def fake_enqueue_execute_target_outbox(session, *, target_id, queue) -> bool:
        return True

    monkeypatch.setattr(
        "app.services.discovery.auto_backfill_service.plan_auto_backfill_posts_targets",
        fake_plan_auto_backfill_posts_targets,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.task_outbox_service.enqueue_execute_target_outbox",
        fake_enqueue_execute_target_outbox,
    )

    def fake_select_top_communities(_: list[str]) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(name="r/startups"),
            SimpleNamespace(name="r/CryptoCurrency"),
        ]

    route = SimpleNamespace(
        warzone="Family_Parenting",
        seed_profiles=[
            SimpleNamespace(name="r/parenting"),
            SimpleNamespace(name="r/NewParents"),
            SimpleNamespace(name="r/BabyBumps"),
        ],
    )

    task = TaskSummary(
        id=uuid4(),
        status="pending",
        product_description="我们是新手父母，夜奶和睡眠记录总断档，家人换手照护时经常漏项，想知道有没有真实可行的产品切口。",
        topic_profile_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        mode="market_insight",
        audit_level="gold",
        membership_level="pro",
    )

    actions = await remediation_module.schedule_auto_backfill_for_insufficient_samples(
        task=task,
        topic_profile=None,
        open_topic_route=route,
        keywords=["父母", "夜奶"],
        select_top_communities_fn=fake_select_top_communities,
    )

    assert planned["communities"] == ["r/parenting", "r/NewParents", "r/BabyBumps"]
    assert actions
    assert actions[0]["type"] == "backfill_posts"
    assert actions[0]["communities"] == ["r/BabyBumps", "r/NewParents", "r/parenting"]
