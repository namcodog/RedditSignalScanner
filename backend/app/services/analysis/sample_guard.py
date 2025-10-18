from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Sequence


SampleFetcher = Callable[..., Awaitable[List[Dict[str, object]]]]
SupplementFetcher = Callable[..., Awaitable[List[Dict[str, object]]]]


@dataclass(slots=True)
class SampleCheckResult:
    """Outcome of the Phase 2 sample floor verification."""

    hot_count: int
    cold_count: int
    combined_count: int
    shortfall: int
    remaining_shortfall: int
    supplemented: bool
    supplement_posts: List[Dict[str, object]]


async def check_sample_size(
    *,
    hot_fetcher: SampleFetcher | None,
    cold_fetcher: SampleFetcher | None,
    supplementer: SupplementFetcher | None,
    keywords: Sequence[str],
    min_samples: int = 1500,
    lookback_days: int = 30,
) -> SampleCheckResult:
    """
    Enforce the minimum sample size contract prior to running the analysis engine.

    Args:
        hot_fetcher: Coroutine returning posts from the hot cache (e.g. PostHot table).
        cold_fetcher: Coroutine returning posts from the cold archive (PostRaw).
        supplementer: Coroutine performing keyword-based crawl when samples are insufficient.
        keywords: Canonical keyword list derived from the product description.
        min_samples: Required minimum combined samples before analysis proceeds.
        lookback_days: Context parameter forwarded to fetchers, indicating the time window.
    """
    hot_posts = (
        await hot_fetcher(lookback_days=lookback_days, keywords=keywords)
        if hot_fetcher
        else []
    )
    cold_posts = (
        await cold_fetcher(lookback_days=lookback_days, keywords=keywords)
        if cold_fetcher
        else []
    )

    hot_count = len(hot_posts)
    cold_count = len(cold_posts)
    combined_count = hot_count + cold_count
    initial_shortfall = max(0, min_samples - combined_count)
    remaining_shortfall = initial_shortfall

    supplement_posts: List[Dict[str, object]] = []
    supplemented = False

    if initial_shortfall > 0 and supplementer:
        supplement_posts = await supplementer(
            keywords=keywords,
            shortfall=initial_shortfall,
            lookback_days=lookback_days,
        )
        for post in supplement_posts:
            post.setdefault("source_type", "search")
        supplemented = bool(supplement_posts)
        combined_count += len(supplement_posts)
        remaining_shortfall = max(0, min_samples - combined_count)

    return SampleCheckResult(
        hot_count=hot_count,
        cold_count=cold_count,
        combined_count=combined_count,
        shortfall=initial_shortfall,
        remaining_shortfall=remaining_shortfall,
        supplemented=supplemented,
        supplement_posts=supplement_posts,
    )


__all__ = ["SampleCheckResult", "check_sample_size"]
