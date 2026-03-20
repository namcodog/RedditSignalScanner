from __future__ import annotations

import pytest

from app.tasks import crawler_task


@pytest.mark.asyncio
async def test_incremental_crawl_delegates_to_patrol_planner_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """增量巡航入口现在是 planner-only，不再直接执行旧版 crawler 主链。"""

    captured: dict[str, object] = {}

    async def fake_runtime(
        *,
        force_refresh: bool,
        build_patrol_planner_workflow_deps_func,
        task_logger,
        module_logger,
    ):  # type: ignore[no-untyped-def]
        captured["force_refresh"] = force_refresh
        captured["deps"] = build_patrol_planner_workflow_deps_func()
        captured["task_logger"] = task_logger
        captured["module_logger"] = module_logger
        return {"status": "planned", "total": 3, "run_id": "r1"}

    def _boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("planner-only path must not instantiate legacy crawler")

    monkeypatch.setattr(crawler_task, "run_patrol_planner_task_runtime", fake_runtime)
    monkeypatch.setattr(crawler_task, "IncrementalCrawler", _boom)
    monkeypatch.setattr(crawler_task, "_build_reddit_client", _boom)

    result = await crawler_task._crawl_seeds_incremental_impl(force_refresh=False)

    deps = captured["deps"]
    assert captured["force_refresh"] is False
    assert deps.load_seed_profiles is crawler_task._load_incremental_seed_profiles
    assert deps.ensure_parent_run is crawler_task._ensure_patrol_parent_run
    assert deps.rank_profiles is crawler_task._rank_patrol_seed_profiles
    assert deps.plan_patrol_targets is crawler_task._plan_patrol_targets_workflow
    assert result == {"status": "planned", "total": 3, "run_id": "r1"}
