from __future__ import annotations

from app.services.community.community_pool_loader import CommunityProfile
from app.services.crawl.patrol_planner_workflow import (
    PatrolPlannerWorkflowDeps,
    PatrolPlannerWorkflowInput,
    run_patrol_planner_workflow,
)


def _profile(name: str, *, tier: str = "high") -> CommunityProfile:
    return CommunityProfile(
        name=name,
        tier=tier,
        categories=[],
        description_keywords={},
        daily_posts=10,
        avg_comment_length=0,
        quality_score=0.5,
        priority="high",
    )


async def test_run_patrol_planner_workflow_returns_idle_and_triggers_probe() -> None:
    probe_calls: list[tuple[int, int]] = []
    warnings: list[str] = []

    async def _load_seed_profiles(force_refresh: bool) -> tuple[list[CommunityProfile], int]:
        assert force_refresh is False
        return [], 12

    async def _maybe_trigger_probe_hot_fallback(*, due_count: int, total_pool_count: int) -> bool:
        probe_calls.append((due_count, total_pool_count))
        return True

    async def _ensure_parent_run(_crawl_run_id: str, _force_refresh: bool) -> None:
        raise AssertionError("idle path should not create parent run")

    async def _rank_profiles(profiles: list[CommunityProfile]) -> list[CommunityProfile]:
        return profiles

    async def _plan_patrol_targets(
        _crawl_run_id: str,
        _profiles: list[CommunityProfile],
        _force_refresh: bool,
    ) -> dict[str, int]:
        raise AssertionError("idle path should not plan targets")

    result = await run_patrol_planner_workflow(
        PatrolPlannerWorkflowInput(force_refresh=False),
        deps=PatrolPlannerWorkflowDeps(
            load_seed_profiles=_load_seed_profiles,
            maybe_trigger_probe_hot_fallback=_maybe_trigger_probe_hot_fallback,
            ensure_parent_run=_ensure_parent_run,
            rank_profiles=_rank_profiles,
            plan_patrol_targets=_plan_patrol_targets,
            generate_run_id=lambda: "run-1",
            log_warning=warnings.append,
        ),
    )

    assert result.status == "idle"
    assert result.total == 12
    assert result.due == 0
    assert probe_calls == [(0, 12)]
    assert warnings == []


async def test_run_patrol_planner_workflow_ranks_profiles_and_plans_targets() -> None:
    call_order: list[str] = []

    async def _load_seed_profiles(force_refresh: bool) -> tuple[list[CommunityProfile], int]:
        assert force_refresh is False
        return [_profile("r/b"), _profile("r/a"), _profile("r/skip", tier="candidate")], 20

    async def _maybe_trigger_probe_hot_fallback(*, due_count: int, total_pool_count: int) -> bool:
        assert due_count == 2
        assert total_pool_count == 20
        call_order.append("probe")
        return False

    async def _ensure_parent_run(crawl_run_id: str, force_refresh: bool) -> None:
        assert crawl_run_id == "run-2"
        assert force_refresh is False
        call_order.append("ensure")

    async def _rank_profiles(profiles: list[CommunityProfile]) -> list[CommunityProfile]:
        call_order.append("rank")
        return list(reversed(profiles))

    async def _plan_patrol_targets(
        crawl_run_id: str,
        profiles: list[CommunityProfile],
        force_refresh: bool,
    ) -> dict[str, int]:
        assert crawl_run_id == "run-2"
        assert force_refresh is False
        assert [profile.name for profile in profiles] == ["r/a", "r/b"]
        call_order.append("plan")
        return {"inserted": 2, "enqueued": 2}

    result = await run_patrol_planner_workflow(
        PatrolPlannerWorkflowInput(force_refresh=False),
        deps=PatrolPlannerWorkflowDeps(
            load_seed_profiles=_load_seed_profiles,
            maybe_trigger_probe_hot_fallback=_maybe_trigger_probe_hot_fallback,
            ensure_parent_run=_ensure_parent_run,
            rank_profiles=_rank_profiles,
            plan_patrol_targets=_plan_patrol_targets,
            generate_run_id=lambda: "run-2",
            log_warning=lambda _msg: None,
        ),
    )

    assert result.status == "planned"
    assert result.run_id == "run-2"
    assert result.total == 20
    assert result.due == 2
    assert result.inserted == 2
    assert result.enqueued == 2
    assert call_order == ["probe", "ensure", "rank", "plan"]
