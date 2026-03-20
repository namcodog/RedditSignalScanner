from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.services.crawl.seed_crawl_runner_workflow import (
    SeedCrawlRunnerWorkflowDeps,
    SeedCrawlRunnerWorkflowInput,
    run_seed_crawl_with_fallback,
)


@dataclass
class _Fallback:
    widen_time_filter_to: str | None = None
    relax_sort_mix: dict[str, float] | None = None
    allow_unfiltered_on_exhausted: bool = False


@dataclass
class _TierCfg:
    post_limit: int = 50
    time_filter: str = "month"
    hot_cache_ttl_hours: int = 24
    fallback: _Fallback | None = None

    def pick_sort(self, default_sort: str) -> str:
        return default_sort


@dataclass
class _Profile:
    name: str
    tier: str = "high"


@pytest.mark.asyncio
async def test_run_seed_crawl_with_fallback_returns_first_success_without_retry() -> None:
    calls: list[dict[str, Any]] = []

    async def _crawl_single(
        community_name: str,
        *,
        settings: Any,
        cache_manager: Any,
        reddit_client: Any,
        post_limit: int,
        time_filter: str | None = None,
        sort: str | None = None,
        hot_cache_ttl_hours: int | None = None,
        tier_name: str | None = None,
    ) -> dict[str, Any]:
        calls.append({"community": community_name, "time_filter": time_filter, "sort": sort})
        return {"community": community_name, "posts_count": 3, "status": "success"}

    result = await run_seed_crawl_with_fallback(
        workflow_input=SeedCrawlRunnerWorkflowInput(
            profile=_Profile(name="r/TestSub"),
            settings=object(),
            cache_manager=object(),
            reddit_client=object(),
            tier_cfg=_TierCfg(),
            default_time_filter="month",
            default_sort="hot",
        ),
        deps=SeedCrawlRunnerWorkflowDeps(
            crawl_single=_crawl_single,
            log_swallowed_exception=lambda *_args, **_kwargs: None,
        ),
    )

    assert result["posts_count"] == 3
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_seed_crawl_with_fallback_applies_widen_or_relax_retry() -> None:
    calls: list[dict[str, Any]] = []

    async def _crawl_single(
        community_name: str,
        *,
        settings: Any,
        cache_manager: Any,
        reddit_client: Any,
        post_limit: int,
        time_filter: str | None = None,
        sort: str | None = None,
        hot_cache_ttl_hours: int | None = None,
        tier_name: str | None = None,
    ) -> dict[str, Any]:
        calls.append({"community": community_name, "time_filter": time_filter, "sort": sort})
        if len(calls) == 1:
            return {"community": community_name, "posts_count": 0, "status": "success"}
        return {"community": community_name, "posts_count": 4, "status": "success"}

    result = await run_seed_crawl_with_fallback(
        workflow_input=SeedCrawlRunnerWorkflowInput(
            profile=_Profile(name="r/TestSub"),
            settings=object(),
            cache_manager=object(),
            reddit_client=object(),
            tier_cfg=_TierCfg(
                fallback=_Fallback(
                    widen_time_filter_to="year",
                    relax_sort_mix={"new": 0.2, "top": 0.8},
                )
            ),
            default_time_filter="month",
            default_sort="hot",
        ),
        deps=SeedCrawlRunnerWorkflowDeps(
            crawl_single=_crawl_single,
            log_swallowed_exception=lambda *_args, **_kwargs: None,
        ),
    )

    assert result["posts_count"] == 4
    assert result["fallback_applied"] == "widen_or_relax"
    assert len(calls) == 2
    assert calls[1]["time_filter"] == "year"
    assert calls[1]["sort"] == "top"


@pytest.mark.asyncio
async def test_run_seed_crawl_with_fallback_applies_unfiltered_retry() -> None:
    calls: list[dict[str, Any]] = []

    async def _crawl_single(
        community_name: str,
        *,
        settings: Any,
        cache_manager: Any,
        reddit_client: Any,
        post_limit: int,
        time_filter: str | None = None,
        sort: str | None = None,
        hot_cache_ttl_hours: int | None = None,
        tier_name: str | None = None,
    ) -> dict[str, Any]:
        calls.append(
            {
                "community": community_name,
                "time_filter": time_filter,
                "sort": sort,
                "post_limit": post_limit,
            }
        )
        if len(calls) < 3:
            return {"community": community_name, "posts_count": 0, "status": "success"}
        return {"community": community_name, "posts_count": 2, "status": "success"}

    result = await run_seed_crawl_with_fallback(
        workflow_input=SeedCrawlRunnerWorkflowInput(
            profile=_Profile(name="r/TestSub"),
            settings=object(),
            cache_manager=object(),
            reddit_client=object(),
            tier_cfg=_TierCfg(
                post_limit=40,
                fallback=_Fallback(
                    widen_time_filter_to="year",
                    relax_sort_mix={"new": 0.2, "top": 0.8},
                    allow_unfiltered_on_exhausted=True,
                ),
            ),
            default_time_filter="month",
            default_sort="hot",
        ),
        deps=SeedCrawlRunnerWorkflowDeps(
            crawl_single=_crawl_single,
            log_swallowed_exception=lambda *_args, **_kwargs: None,
        ),
    )

    assert result["posts_count"] == 2
    assert result["fallback_applied"] == "unfiltered_all"
    assert len(calls) == 3
    assert calls[2]["time_filter"] == "all"
    assert calls[2]["sort"] == "top"
    assert calls[2]["post_limit"] == 48
