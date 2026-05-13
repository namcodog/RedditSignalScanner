from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from app.services.crawl.comprehensive_crawl_workflow import ComprehensiveCrawlWorkflowDeps
from app.services.crawl.incremental_crawl_workflow import IncrementalCrawlWorkflowDeps
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost


@dataclass(slots=True)
class IncrementalCrawlerDepsFactoryInput:
    reddit_client: RedditAPIClient | None
    get_watermark: Callable[[str], Awaitable[datetime | None]]
    filter_spam_posts: Callable[[str, list[RedditPost]], list[RedditPost]]
    dual_write: Callable[[str, list[RedditPost]], Awaitable[tuple[int, int, int]]]
    dispatch_score_refresh: Callable[[int], Awaitable[None]]
    update_watermark: Callable[..., Awaitable[None]]
    record_failure_attempt: Callable[[str, datetime], Awaitable[None]]
    record_empty_attempt: Callable[[str, datetime], Awaitable[None]]
    record_crawl_metrics: Callable[..., Awaitable[None]]
    normalize_subreddit_name: Callable[[str], str]
    unix_to_datetime: Callable[[float], datetime]


def build_incremental_crawl_workflow_deps(
    factory_input: IncrementalCrawlerDepsFactoryInput,
) -> IncrementalCrawlWorkflowDeps:
    async def _fetch_posts(
        subreddit: str,
        limit: int,
        time_filter: str,
        sort: str,
    ) -> Any:
        if not factory_input.reddit_client:
            raise ValueError("RedditAPIClient is required for crawling")
        return await factory_input.reddit_client.fetch_subreddit_posts(
            subreddit,
            limit=limit,
            time_filter=time_filter,
            sort=sort,
        )

    return IncrementalCrawlWorkflowDeps(
        get_watermark=factory_input.get_watermark,
        fetch_posts=_fetch_posts,
        filter_spam_posts=factory_input.filter_spam_posts,
        dual_write=factory_input.dual_write,
        dispatch_score_refresh=factory_input.dispatch_score_refresh,
        update_watermark=factory_input.update_watermark,
        record_failure_attempt=factory_input.record_failure_attempt,
        record_empty_attempt=factory_input.record_empty_attempt,
        record_crawl_metrics=factory_input.record_crawl_metrics,
    )


def build_comprehensive_crawl_workflow_deps(
    factory_input: IncrementalCrawlerDepsFactoryInput,
) -> ComprehensiveCrawlWorkflowDeps:
    async def _fetch_comprehensive_posts(
        subreddit: str,
        time_filter: str,
        max_per_strategy: int,
    ) -> Any:
        if not factory_input.reddit_client:
            raise ValueError("RedditAPIClient is required for crawling")
        return await factory_input.reddit_client.fetch_comprehensive_posts(
            subreddit,
            time_filter=time_filter,
            max_per_strategy=max_per_strategy,
        )

    async def _update_comprehensive_watermark(
        community_name: str,
        latest_post_id: str,
        latest_created_at: datetime,
        total_fetched: int,
        new_valid_posts: int,
        dedup_rate: float,
    ) -> None:
        await factory_input.update_watermark(
            community_name,
            latest_post_id,
            latest_created_at,
            total_fetched=total_fetched,
            new_valid_posts=new_valid_posts,
            dedup_rate=dedup_rate,
        )

    return ComprehensiveCrawlWorkflowDeps(
        normalize_subreddit_name=factory_input.normalize_subreddit_name,
        get_watermark=factory_input.get_watermark,
        fetch_comprehensive_posts=_fetch_comprehensive_posts,
        unix_to_datetime=factory_input.unix_to_datetime,
        filter_spam_posts=lambda community_name, posts: factory_input.filter_spam_posts(
            community_name, list(posts)
        ),
        dual_write=lambda community_name, posts: factory_input.dual_write(
            community_name, list(posts)
        ),
        update_watermark=_update_comprehensive_watermark,
    )


__all__ = [
    "IncrementalCrawlerDepsFactoryInput",
    "build_comprehensive_crawl_workflow_deps",
    "build_incremental_crawl_workflow_deps",
]
