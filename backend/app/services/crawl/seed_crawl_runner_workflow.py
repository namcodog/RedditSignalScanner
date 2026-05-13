from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(slots=True)
class SeedCrawlRunnerWorkflowInput:
    profile: Any
    settings: Any
    cache_manager: Any
    reddit_client: Any
    tier_cfg: Any | None
    default_time_filter: str
    default_sort: str


@dataclass(slots=True)
class SeedCrawlRunnerWorkflowDeps:
    crawl_single: Callable[..., Awaitable[dict[str, Any]]]
    log_swallowed_exception: Callable[[str, Exception], None]


async def run_seed_crawl_with_fallback(
    *,
    workflow_input: SeedCrawlRunnerWorkflowInput,
    deps: SeedCrawlRunnerWorkflowDeps,
) -> dict[str, Any]:
    profile = workflow_input.profile
    tier_cfg = workflow_input.tier_cfg
    post_limit = tier_cfg.post_limit if tier_cfg else 100
    time_filter = tier_cfg.time_filter if tier_cfg else workflow_input.default_time_filter
    sort = (
        tier_cfg.pick_sort(default_sort=workflow_input.default_sort)
        if tier_cfg
        else workflow_input.default_sort
    )
    ttl_hours = tier_cfg.hot_cache_ttl_hours if tier_cfg else 48

    result = await deps.crawl_single(
        profile.name,
        settings=workflow_input.settings,
        cache_manager=workflow_input.cache_manager,
        reddit_client=workflow_input.reddit_client,
        post_limit=post_limit,
        time_filter=time_filter,
        sort=sort,
        hot_cache_ttl_hours=ttl_hours,
        tier_name=profile.tier,
    )

    try:
        fallback = getattr(tier_cfg, "fallback", None)
        if (
            result.get("status") == "success"
            and int(result.get("posts_count", 0) or 0) == 0
            and fallback is not None
        ):
            widened = False
            new_filter = time_filter
            new_sort = sort
            if getattr(fallback, "widen_time_filter_to", None):
                new_filter = str(fallback.widen_time_filter_to)
                widened = True
            relax = getattr(fallback, "relax_sort_mix", None)
            if isinstance(relax, dict) and relax:
                new_sort = max(
                    relax.items(),
                    key=lambda item: (float(item[1] or 0.0), str(item[0])),
                )[0]
            if widened or relax:
                retry1 = await deps.crawl_single(
                    profile.name,
                    settings=workflow_input.settings,
                    cache_manager=workflow_input.cache_manager,
                    reddit_client=workflow_input.reddit_client,
                    post_limit=post_limit,
                    time_filter=new_filter,
                    sort=new_sort,
                    hot_cache_ttl_hours=ttl_hours,
                    tier_name=profile.tier,
                )
                if int(retry1.get("posts_count", 0) or 0) > 0:
                    retry1["fallback_applied"] = "widen_or_relax"
                    return retry1
                result = retry1
            if getattr(fallback, "allow_unfiltered_on_exhausted", False):
                retry2 = await deps.crawl_single(
                    profile.name,
                    settings=workflow_input.settings,
                    cache_manager=workflow_input.cache_manager,
                    reddit_client=workflow_input.reddit_client,
                    post_limit=min(120, int(post_limit * 1.2)),
                    time_filter="all",
                    sort="top",
                    hot_cache_ttl_hours=ttl_hours,
                    tier_name=profile.tier,
                )
                if int(retry2.get("posts_count", 0) or 0) > 0:
                    retry2["fallback_applied"] = "unfiltered_all"
                    return retry2
                result = retry2
    except Exception as exc:
        deps.log_swallowed_exception(
            f"crawl fallback failed for {profile.name}",
            exc,
        )

    return result


__all__ = [
    "SeedCrawlRunnerWorkflowDeps",
    "SeedCrawlRunnerWorkflowInput",
    "run_seed_crawl_with_fallback",
]
