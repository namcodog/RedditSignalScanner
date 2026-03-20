from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.crawl.seed_crawl_metrics_service import SeedCrawlMetricsResult
from app.services.crawl.seed_crawl_workflow import (
    SeedCrawlWorkflowDeps,
    SeedCrawlWorkflowInput,
    run_seed_crawl_workflow,
)


class _FakeSession:
    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None


@dataclass
class _Profile:
    name: str
    tier: str


@dataclass
class _PlanEntry:
    profile: _Profile
    status: str = "active"
    crawl_track: str = "seed"


@pytest.mark.asyncio
async def test_seed_crawl_workflow_filters_to_allowed_tiers() -> None:
    seen_profiles: list[str] = []

    class _Loader:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def load_seed_communities(self) -> dict[str, int]:
            return {"loaded": 0}

    class _PlanBuilder:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def build_plan(self) -> list[_PlanEntry]:
            return [
                _PlanEntry(_Profile("r/high", "high")),
                _PlanEntry(_Profile("r/custom", "custom")),
                _PlanEntry(_Profile("r/low", "low")),
            ]

    async def _fake_runner(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        seen_profiles.append(workflow_input.profile.name)
        return {"community": workflow_input.profile.name, "status": "success", "posts_count": 1}

    async def _fake_metrics(*, metrics_input: Any, deps: Any) -> SeedCrawlMetricsResult:
        return SeedCrawlMetricsResult(
            success_count=2,
            failure_count=0,
            empty_count=0,
            total_new=2,
            avg_latency=0.1,
            tier_metrics_payload={"assignments": {"r/high": "high", "r/low": "low"}},
        )

    result = await run_seed_crawl_workflow(
        workflow_input=SeedCrawlWorkflowInput(
            force_refresh=False,
            settings=SimpleNamespace(),
            cache_manager=object(),
            reddit_client=object(),
            session_factory=lambda: _FakeSession(),
            effective_batch_size=10,
            effective_max_concurrency=2,
            effective_time_filter="day",
            effective_sort="top",
        ),
        deps=SeedCrawlWorkflowDeps(
            loader_factory=_Loader,
            plan_builder_factory=_PlanBuilder,
            tier_settings_for=lambda profile: {"tier": profile.tier},
            run_seed_crawl_with_fallback=_fake_runner,
            build_runner_deps=lambda: SimpleNamespace(),
            record_seed_crawl_metrics=_fake_metrics,
            build_metrics_deps=lambda: SimpleNamespace(),
        ),
    )

    assert seen_profiles == ["r/high", "r/low"]
    assert result.payload["total"] == 2
    assert result.payload["succeeded"] == 2


@pytest.mark.asyncio
async def test_seed_crawl_workflow_falls_back_to_all_seeds_when_filter_is_empty() -> None:
    seen_profiles: list[str] = []

    class _Loader:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def load_seed_communities(self) -> dict[str, int]:
            return {"loaded": 0}

    class _PlanBuilder:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def build_plan(self) -> list[_PlanEntry]:
            return [
                _PlanEntry(_Profile("r/custom1", "custom")),
                _PlanEntry(_Profile("r/custom2", "custom")),
            ]

    async def _fake_runner(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        seen_profiles.append(workflow_input.profile.name)
        return {"community": workflow_input.profile.name, "status": "success", "posts_count": 1}

    async def _fake_metrics(*, metrics_input: Any, deps: Any) -> SeedCrawlMetricsResult:
        return SeedCrawlMetricsResult(
            success_count=2,
            failure_count=0,
            empty_count=0,
            total_new=2,
            avg_latency=0.1,
            tier_metrics_payload={"assignments": {"r/custom1": "custom", "r/custom2": "custom"}},
        )

    result = await run_seed_crawl_workflow(
        workflow_input=SeedCrawlWorkflowInput(
            force_refresh=False,
            settings=SimpleNamespace(),
            cache_manager=object(),
            reddit_client=object(),
            session_factory=lambda: _FakeSession(),
            effective_batch_size=10,
            effective_max_concurrency=2,
            effective_time_filter="day",
            effective_sort="top",
        ),
        deps=SeedCrawlWorkflowDeps(
            loader_factory=_Loader,
            plan_builder_factory=_PlanBuilder,
            tier_settings_for=lambda profile: {"tier": profile.tier},
            run_seed_crawl_with_fallback=_fake_runner,
            build_runner_deps=lambda: SimpleNamespace(),
            record_seed_crawl_metrics=_fake_metrics,
            build_metrics_deps=lambda: SimpleNamespace(),
        ),
    )

    assert seen_profiles == ["r/custom1", "r/custom2"]
    assert result.payload["total"] == 2
    assert result.payload["failed"] == 0
