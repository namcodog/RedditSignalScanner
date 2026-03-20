from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncContextManager, Awaitable, Callable, Iterable

from app.services.crawl.seed_crawl_metrics_service import (
    SeedCrawlMetricsInput,
    SeedCrawlMetricsResult,
)
from app.services.crawl.seed_crawl_runner_workflow import (
    SeedCrawlRunnerWorkflowDeps,
    SeedCrawlRunnerWorkflowInput,
)


@dataclass(slots=True)
class SeedCrawlWorkflowInput:
    force_refresh: bool
    settings: Any
    cache_manager: Any
    reddit_client: Any
    session_factory: Callable[[], AsyncContextManager[Any]]
    effective_batch_size: int
    effective_max_concurrency: int
    effective_time_filter: str
    effective_sort: str


@dataclass(slots=True)
class SeedCrawlWorkflowDeps:
    loader_factory: Callable[[Any], Any]
    plan_builder_factory: Callable[[Any], Any]
    tier_settings_for: Callable[[Any], Any]
    run_seed_crawl_with_fallback: Callable[..., Awaitable[dict[str, Any]]]
    build_runner_deps: Callable[[], SeedCrawlRunnerWorkflowDeps]
    record_seed_crawl_metrics: Callable[..., Awaitable[SeedCrawlMetricsResult]]
    build_metrics_deps: Callable[[], Any]


@dataclass(slots=True)
class SeedCrawlWorkflowResult:
    payload: dict[str, Any]


def _chunked(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


async def run_seed_crawl_workflow(
    *,
    workflow_input: SeedCrawlWorkflowInput,
    deps: SeedCrawlWorkflowDeps,
) -> SeedCrawlWorkflowResult:
    async with workflow_input.session_factory() as db:
        loader = deps.loader_factory(db)
        plan_builder = deps.plan_builder_factory(db)
        if workflow_input.force_refresh:
            await loader.load_seed_communities()

        plan = await plan_builder.build_plan()
        seeds = [
            entry.profile
            for entry in plan
            if entry.status == "active" and entry.crawl_track != "none"
        ]

    allowed_tiers = {"high", "medium", "low", "gold", "silver", "seed"}
    seed_profiles = [profile for profile in seeds if profile.tier.lower() in allowed_tiers]
    if not seed_profiles:
        seed_profiles = list(seeds)

    semaphore = asyncio.Semaphore(max(1, workflow_input.effective_max_concurrency))
    results: list[dict[str, Any]] = []

    async def runner(profile: Any) -> dict[str, Any]:
        async with semaphore:
            return await deps.run_seed_crawl_with_fallback(
                workflow_input=SeedCrawlRunnerWorkflowInput(
                    profile=profile,
                    settings=workflow_input.settings,
                    cache_manager=workflow_input.cache_manager,
                    reddit_client=workflow_input.reddit_client,
                    tier_cfg=deps.tier_settings_for(profile),
                    default_time_filter=workflow_input.effective_time_filter,
                    default_sort=workflow_input.effective_sort,
                ),
                deps=deps.build_runner_deps(),
            )

    for batch in _chunked(seed_profiles, workflow_input.effective_batch_size):
        batch_results = await asyncio.gather(
            *[runner(profile) for profile in batch],
            return_exceptions=True,
        )
        for profile, outcome in zip(batch, batch_results):
            if isinstance(outcome, Exception):
                results.append(
                    {
                        "community": profile.name,
                        "status": "failed",
                        "error": str(outcome),
                    }
                )
            else:
                results.append(outcome)

    metrics_result = await deps.record_seed_crawl_metrics(
        metrics_input=SeedCrawlMetricsInput(
            results=results,
            total_profiles=len(seed_profiles),
        ),
        deps=deps.build_metrics_deps(),
    )

    return SeedCrawlWorkflowResult(
        payload={
            "status": "completed",
            "total": len(seed_profiles),
            "succeeded": metrics_result.success_count,
            "failed": metrics_result.failure_count,
            "communities": results,
            "tier_assignments": metrics_result.tier_metrics_payload,
        }
    )


__all__ = [
    "SeedCrawlWorkflowInput",
    "SeedCrawlWorkflowDeps",
    "SeedCrawlWorkflowResult",
    "run_seed_crawl_workflow",
]
