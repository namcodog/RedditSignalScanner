from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.services.community.blacklist_loader import BlacklistConfig
from app.services.crawl.comprehensive_crawl_workflow import ComprehensiveCrawlWorkflowDeps
from app.services.crawl.crawl_metrics_service import (
    CrawlMetricsDeps,
    CrawlMetricsInput,
    record_crawl_metrics,
)
from app.services.crawl.incremental_content_filter_service import (
    IncrementalDuplicateLookupDeps,
    IncrementalSpamFilterDeps,
    IncrementalSpamFilterInput,
    classify_spam_post,
    filter_incremental_spam_posts,
    find_incremental_content_duplicate,
)
from app.services.crawl.incremental_crawler_deps_factory import (
    IncrementalCrawlerDepsFactoryInput,
    build_comprehensive_crawl_workflow_deps,
    build_incremental_crawl_workflow_deps,
)
from app.services.crawl.incremental_crawl_workflow import IncrementalCrawlWorkflowDeps
from app.services.crawl.incremental_cold_storage_service import (
    ColdStorageUpsertDeps,
    ColdStorageUpsertInput,
    ColdStorageUpsertResult,
    upsert_post_to_cold_storage,
)
from app.services.crawl.incremental_hot_cache_service import (
    HotCacheUpsertDeps,
    HotCacheUpsertInput,
    upsert_post_to_hot_cache,
)
from app.services.crawl.incremental_post_persistence_service import (
    DualWriteDeps,
    DualWriteInput,
    execute_dual_write,
)
from app.services.crawl.incremental_runtime_deps_factory import IncrementalRuntimeDeps
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost


@dataclass(slots=True)
class IncrementalCrawlerRuntimeInput:
    db: AsyncSession
    reddit_client: RedditAPIClient | None
    runtime_deps: IncrementalRuntimeDeps
    blacklist: BlacklistConfig | None
    hot_cache_ttl_hours: int
    refresh_posts_latest_after_write: bool
    source_track: str
    crawl_run_id: str | None
    community_run_id: str | None
    spam_filter_mode: str
    duplicate_mode: str
    spam_classifier: Callable[[RedditPost], str | None] | None
    normalize_subreddit_name: Callable[[str], str]
    unix_to_datetime: Callable[[float], datetime]
    text_norm_hash_available: Callable[[], Awaitable[bool]]
    posts_raw_has_crawl_run_id: Callable[[AsyncSession], Awaitable[bool]]
    posts_raw_has_community_run_id: Callable[[AsyncSession], Awaitable[bool]]
    is_current_unique_violation: Callable[[Exception], bool]


class IncrementalCrawlerRuntime:
    def __init__(self, runtime_input: IncrementalCrawlerRuntimeInput) -> None:
        self.db = runtime_input.db
        self.reddit_client = runtime_input.reddit_client
        self.runtime_deps = runtime_input.runtime_deps
        self.blacklist = runtime_input.blacklist
        self.hot_cache_ttl_hours = runtime_input.hot_cache_ttl_hours
        self.refresh_posts_latest_after_write = runtime_input.refresh_posts_latest_after_write
        self.source_track = runtime_input.source_track
        self.crawl_run_id = runtime_input.crawl_run_id
        self.community_run_id = runtime_input.community_run_id
        self.spam_filter_mode = runtime_input.spam_filter_mode
        self.duplicate_mode = runtime_input.duplicate_mode
        self.spam_classifier = runtime_input.spam_classifier
        self.normalize_subreddit_name = runtime_input.normalize_subreddit_name
        self.unix_to_datetime = runtime_input.unix_to_datetime
        self.text_norm_hash_available = runtime_input.text_norm_hash_available
        self.posts_raw_has_crawl_run_id = runtime_input.posts_raw_has_crawl_run_id
        self.posts_raw_has_community_run_id = runtime_input.posts_raw_has_community_run_id
        self.is_current_unique_violation = runtime_input.is_current_unique_violation
        self._crawler_run_row_ensured = False
        self._spam_categories: dict[str, str] = {}

    def build_incremental_workflow_deps(self) -> IncrementalCrawlWorkflowDeps:
        return build_incremental_crawl_workflow_deps(
            IncrementalCrawlerDepsFactoryInput(
                reddit_client=self.reddit_client,
                get_watermark=self.get_watermark,
                filter_spam_posts=self.filter_spam_posts,
                dual_write=lambda community_name, posts: self.dual_write(
                    community_name,
                    posts,
                    trigger_comments_fetch=True,
                ),
                dispatch_score_refresh=self.runtime_deps.dispatch_score_refresh,
                update_watermark=self.runtime_deps.update_watermark,
                record_failure_attempt=self.runtime_deps.record_failure_attempt,
                record_empty_attempt=self.runtime_deps.record_empty_attempt,
                record_crawl_metrics=self.record_crawl_metrics,
                normalize_subreddit_name=self.normalize_subreddit_name,
                unix_to_datetime=self.unix_to_datetime,
            )
        )

    def build_comprehensive_workflow_deps(self) -> ComprehensiveCrawlWorkflowDeps:
        return build_comprehensive_crawl_workflow_deps(
            IncrementalCrawlerDepsFactoryInput(
                reddit_client=self.reddit_client,
                get_watermark=self.get_watermark,
                filter_spam_posts=self.filter_spam_posts,
                dual_write=lambda community_name, posts: self.dual_write(
                    community_name,
                    list(posts),
                ),
                dispatch_score_refresh=self.runtime_deps.dispatch_score_refresh,
                update_watermark=self.runtime_deps.update_watermark,
                record_failure_attempt=self.runtime_deps.record_failure_attempt,
                record_empty_attempt=self.runtime_deps.record_empty_attempt,
                record_crawl_metrics=self.record_crawl_metrics,
                normalize_subreddit_name=self.normalize_subreddit_name,
                unix_to_datetime=self.unix_to_datetime,
            )
        )

    def is_spam_post(self, post: RedditPost) -> str | None:
        return classify_spam_post(post, blacklist=self.blacklist)

    def filter_spam_posts(
        self,
        community_name: str,
        posts: list[RedditPost],
    ) -> list[RedditPost]:
        return filter_incremental_spam_posts(
            IncrementalSpamFilterInput(
                community_name=community_name,
                posts=posts,
                spam_filter_mode=self.spam_filter_mode,
            ),
            IncrementalSpamFilterDeps(
                blacklist=self.blacklist,
                spam_categories=self._spam_categories,
                spam_classifier=self.spam_classifier or self.is_spam_post,
            ),
        )

    async def find_content_duplicate(
        self,
        subreddit: str,
        post: RedditPost,
    ) -> str | None:
        return await find_incremental_content_duplicate(
            subreddit=subreddit,
            post=post,
            deps=IncrementalDuplicateLookupDeps(
                text_norm_hash_available=self.text_norm_hash_available,
                execute_query=self.db.execute,
            ),
        )

    async def get_watermark(self, community_name: str) -> Optional[datetime]:
        result = await self.db.execute(
            select(CommunityCache.last_seen_created_at).where(
                CommunityCache.community_name == community_name
            )
        )
        row = result.scalar_one_or_none()
        return row if row else None

    async def dual_write(
        self,
        community_name: str,
        posts: list[RedditPost],
        *,
        trigger_comments_fetch: bool = False,
    ) -> tuple[int, int, int]:
        result = await execute_dual_write(
            write_input=DualWriteInput(
                community_name=community_name,
                posts=posts,
                trigger_comments_fetch=trigger_comments_fetch,
                refresh_posts_latest_after_write=self.refresh_posts_latest_after_write,
            ),
            deps=DualWriteDeps(
                db=self.db,
                upsert_to_cold_storage=self.upsert_to_cold_storage,
                upsert_to_hot_cache=self.upsert_to_hot_cache,
                is_current_unique_violation=self.is_current_unique_violation,
                schedule_posts_latest_refresh=self.runtime_deps.schedule_posts_latest_refresh,
                enqueue_comment_backfill=self.runtime_deps.enqueue_comment_backfill,
            ),
        )
        return result.new_count, result.updated_count, result.duplicate_count

    async def upsert_to_cold_storage(
        self,
        community_name: str,
        post: RedditPost,
    ) -> tuple[bool, bool]:
        result: ColdStorageUpsertResult = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name=community_name,
                post=post,
                source_track=self.source_track,
                crawl_run_id=self.crawl_run_id,
                community_run_id=self.community_run_id,
                duplicate_mode=self.duplicate_mode,
                spam_categories=self._spam_categories,
                crawler_run_row_ensured=self._crawler_run_row_ensured,
            ),
            deps=ColdStorageUpsertDeps(
                db=self.db,
                ensure_author=self.runtime_deps.ensure_author,
                find_content_duplicate=self.find_content_duplicate,
                unix_to_datetime=self.unix_to_datetime,
                posts_raw_has_crawl_run_id=self.posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=self.posts_raw_has_community_run_id,
            ),
        )
        self._crawler_run_row_ensured = result.crawler_run_row_ensured
        return result.is_new, result.is_updated

    async def upsert_to_hot_cache(
        self,
        community_name: str,
        post: RedditPost,
    ) -> None:
        await upsert_post_to_hot_cache(
            write_input=HotCacheUpsertInput(
                community_name=community_name,
                post=post,
                hot_cache_ttl_hours=self.hot_cache_ttl_hours,
            ),
            deps=HotCacheUpsertDeps(
                db=self.db,
                ensure_author=self.runtime_deps.ensure_author,
                unix_to_datetime=self.unix_to_datetime,
            ),
        )

    async def record_crawl_metrics(
        self,
        successful_crawls: int = 0,
        empty_crawls: int = 0,
        failed_crawls: int = 0,
        total_new_posts: int = 0,
        total_updated_posts: int = 0,
        total_duplicates: int = 0,
        avg_latency_seconds: float = 0.0,
    ) -> None:
        await record_crawl_metrics(
            metrics_input=CrawlMetricsInput(
                successful_crawls=successful_crawls,
                empty_crawls=empty_crawls,
                failed_crawls=failed_crawls,
                total_new_posts=total_new_posts,
                total_updated_posts=total_updated_posts,
                total_duplicates=total_duplicates,
                avg_latency_seconds=avg_latency_seconds,
            ),
            deps=CrawlMetricsDeps(db=self.db),
        )


__all__ = [
    "IncrementalCrawlerRuntime",
    "IncrementalCrawlerRuntimeInput",
]
