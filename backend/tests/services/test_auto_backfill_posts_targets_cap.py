from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.discovery import auto_backfill_service as svc


class _DummySession:
    pass


@pytest.mark.asyncio
async def test_plan_auto_backfill_posts_targets_respects_max_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    created_targets: list[str] = []

    async def _ensure_run(session, *, crawl_run_id: str, config: dict) -> None:  # type: ignore[no-untyped-def]
        return None

    async def _ensure_target(session, *, community_run_id: str, **kwargs):  # type: ignore[no-untyped-def]
        created_targets.append(str(community_run_id))
        return True

    monkeypatch.setattr(svc, "ensure_crawler_run", _ensure_run)
    monkeypatch.setattr(svc, "ensure_crawler_run_target", _ensure_target)

    now = datetime(2025, 12, 29, 0, 0, 0, tzinfo=timezone.utc)
    targets = await svc.plan_auto_backfill_posts_targets(
        session=_DummySession(),  # type: ignore[arg-type]
        crawl_run_id="00000000-0000-0000-0000-000000000000",
        communities=["r/shopify", "r/facebookads"],
        now=now,
        days=30,
        slice_days=7,
        total_posts_budget=300,
        max_targets=3,
        reason="test",
    )
    assert len(targets) == 3
    assert len(created_targets) == 3

