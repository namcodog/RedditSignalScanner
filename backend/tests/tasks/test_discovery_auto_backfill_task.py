from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_community_evaluation_auto_backfill_enqueues_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import discovery_task

    monkeypatch.setenv("DISCOVERY_AUTO_BACKFILL_ENABLED", "1")

    class DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

    class DummyEvaluator:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

        async def evaluate_all_pending(self) -> list[dict[str, Any]]:
            return [
                {"community": "r/test_auto_backfill", "status": "approved"},
                {"community": "r/test_rejected", "status": "rejected"},
            ]

    sent: list[dict[str, Any]] = []

    async def fake_enqueue_execute_target_outbox(
        *_: Any, target_id: str, queue: str, **__: Any
    ) -> bool:
        sent.append({"target_id": target_id, "queue": queue})
        return True

    called: dict[str, Any] = {}

    async def fake_plan_auto_backfill_posts_targets(
        *,
        session: Any,
        crawl_run_id: str,
        communities: list[str],
        now: Any,
        days: int,
        slice_days: int,
        total_posts_budget: int,
        reason: str,
    ) -> list[str]:
        called["crawl_run_id"] = crawl_run_id
        called["communities"] = communities
        called["days"] = days
        called["slice_days"] = slice_days
        called["total_posts_budget"] = total_posts_budget
        called["reason"] = reason
        return ["t1", "t2"]

    monkeypatch.setattr(discovery_task, "RedditAPIClient", DummyRedditClient)
    monkeypatch.setattr(discovery_task, "CommunityEvaluator", DummyEvaluator)
    monkeypatch.setattr(
        discovery_task, "enqueue_execute_target_outbox", fake_enqueue_execute_target_outbox
    )
    monkeypatch.setattr(
        discovery_task,
        "plan_auto_backfill_posts_targets",
        fake_plan_auto_backfill_posts_targets,
    )

    results = await discovery_task._run_community_evaluation()

    assert isinstance(results, list)
    assert called["communities"] == ["r/test_auto_backfill"]
    assert called["days"] == 30
    assert called["slice_days"] == 7
    assert called["total_posts_budget"] == 300
    assert called["reason"] == "auto_backfill_after_approval"

    assert [s["queue"] for s in sent] == [
        "backfill_posts_queue_v2",
        "backfill_posts_queue_v2",
    ]
    assert [s["target_id"] for s in sent] == ["t1", "t2"]
