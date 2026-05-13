from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_crawl_low_quality_communities_impl_delegates_to_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    async def _fake_workflow(params, *, deps):  # type: ignore[no-untyped-def]
        assert params.stale_hours == 8
        assert params.max_targets == 50
        assert params.posts_limit == 100
        assert params.time_filter == crawler_task.DEFAULT_TIME_FILTER
        assert params.sort == crawler_task.DEFAULT_SORT
        assert params.hot_cache_ttl_hours == int(crawler_task.EFFECTIVE_HOT_CACHE_TTL_HOURS)
        assert deps is not None

        class _Result:
            status = "planned"
            inserted = 3
            enqueued = 3
            run_id = "run-123"
            total = 5

            def as_dict(self) -> dict[str, object]:
                return {
                    "status": self.status,
                    "inserted": self.inserted,
                    "enqueued": self.enqueued,
                    "run_id": self.run_id,
                    "total": self.total,
                }

        return _Result()

    monkeypatch.setattr(
        crawler_task,
        "plan_low_quality_communities_workflow",
        _fake_workflow,
    )

    result = await crawler_task._crawl_low_quality_communities_impl()

    assert result == {
        "status": "planned",
        "mode": "low_quality_patrol_planner",
        "run_id": "run-123",
        "total": 5,
        "inserted": 3,
        "enqueued": 3,
    }
