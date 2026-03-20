"""
增量抓取服务：冷热双写 + 水位线机制
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.posts_storage import PostHot, PostRaw
from app.services.crawl.comprehensive_crawl_workflow import (
    ComprehensiveCrawlWorkflowInput,
    run_comprehensive_crawl_workflow,
)
from app.services.crawl.incremental_crawler_runtime import (
    IncrementalCrawlerRuntime,
    IncrementalCrawlerRuntimeInput,
)
from app.services.crawl.incremental_crawl_workflow import (
    IncrementalCrawlWorkflowInput,
    run_incremental_crawl_workflow,
)
from app.services.crawl.incremental_runtime_deps_factory import (
    IncrementalRuntimeDeps,
    IncrementalRuntimeDepsFactoryInput,
    build_incremental_runtime_deps,
)
from app.services.crawl.ingest_posts_batch_service import (
    IngestPostsBatchDeps,
    IngestPostsBatchInput,
    ingest_posts_batch as run_ingest_posts_batch,
)
from app.services.crawl.backfill_posts_workflow import (
    BackfillPostsWorkflowDeps,
    BackfillPostsWorkflowInput,
    execute_backfill_posts_workflow,
)
from app.services.community.community_cache_service import (
    mark_crawl_attempt,
    update_backfill_floor_if_lower,
    update_backfill_cursor,
    update_incremental_waterline_if_forward,
)
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.utils.subreddit import normalize_subreddit_name
from app.services.community.blacklist_loader import BlacklistConfig

logger = logging.getLogger(__name__)

_POSTS_RAW_HAS_CRAWL_RUN_ID: bool | None = None
_POSTS_RAW_HAS_COMMUNITY_RUN_ID: bool | None = None
_TEXT_NORM_HASH_AVAILABLE: bool | None = None


async def _posts_raw_has_crawl_run_id(session: AsyncSession) -> bool:
    global _POSTS_RAW_HAS_CRAWL_RUN_ID
    if _POSTS_RAW_HAS_CRAWL_RUN_ID is not None:
        return _POSTS_RAW_HAS_CRAWL_RUN_ID
    res = await session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='posts_raw'
              AND column_name='crawl_run_id'
            LIMIT 1
            """
        )
    )
    _POSTS_RAW_HAS_CRAWL_RUN_ID = res.scalar_one_or_none() is not None
    return _POSTS_RAW_HAS_CRAWL_RUN_ID


async def _posts_raw_has_community_run_id(session: AsyncSession) -> bool:
    global _POSTS_RAW_HAS_COMMUNITY_RUN_ID
    if _POSTS_RAW_HAS_COMMUNITY_RUN_ID is not None:
        return _POSTS_RAW_HAS_COMMUNITY_RUN_ID
    res = await session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='posts_raw'
              AND column_name='community_run_id'
            LIMIT 1
            """
        )
    )
    _POSTS_RAW_HAS_COMMUNITY_RUN_ID = res.scalar_one_or_none() is not None
    return _POSTS_RAW_HAS_COMMUNITY_RUN_ID


async def _text_norm_hash_available(session: AsyncSession) -> bool:
    global _TEXT_NORM_HASH_AVAILABLE
    if _TEXT_NORM_HASH_AVAILABLE is not None:
        return _TEXT_NORM_HASH_AVAILABLE
    res = await session.execute(
        text(
            """
            SELECT 1
            FROM pg_proc
            WHERE proname = 'text_norm_hash'
            LIMIT 1
            """
        )
    )
    _TEXT_NORM_HASH_AVAILABLE = res.scalar_one_or_none() is not None
    return _TEXT_NORM_HASH_AVAILABLE


def _unix_to_datetime(unix_timestamp: float) -> datetime:
    """将 Unix 时间戳转换为 UTC datetime"""
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)


def _is_current_unique_violation(exc: IntegrityError) -> bool:
    raw = str(getattr(exc, "orig", "") or exc)
    return "ux_posts_raw_current" in raw


class IncrementalCrawler:
    """
    增量抓取器：实现冷热双写 + 水位线机制

    核心原则：
    1. 先写冷库（持久层），再写热缓存
    2. 使用水位线避免重复抓取
    3. 去重策略：(source, source_post_id, text_norm_hash)
    4. SCD2 版本追踪
    """

    def __init__(
        self,
        db: AsyncSession,
        reddit_client: RedditAPIClient = None,  # Allow optional client for pure ingestion
        # Align with crawler.yml: default 4320h (180 days); avoids fallback to 30d when config missing.
        hot_cache_ttl_hours: int = 4320,
        *,
        refresh_posts_latest_after_write: bool = True,
        source_track: str = "incremental",
        crawl_run_id: str | None = None,
        community_run_id: str | None = None,
        spam_filter_mode: str | None = None,
        duplicate_mode: str | None = None,
        enable_comments_backfill: bool | None = None,
        comments_backfill_mode: str | None = None,
        comments_backfill_max_posts: int | None = None,
        comments_backfill_limit: int | None = None,
        comments_backfill_depth: int | None = None,
    ):
        self.db = db
        self.reddit_client = reddit_client
        self.hot_cache_ttl_hours = hot_cache_ttl_hours
        self.refresh_posts_latest_after_write = refresh_posts_latest_after_write
        self.source_track = source_track
        self.crawl_run_id = crawl_run_id
        self.community_run_id = community_run_id
        self._crawler_run_row_ensured = False
        self._spam_categories: dict[str, str] = {}
        raw_spam_mode = (spam_filter_mode or settings.incremental_spam_filter_mode or "drop").strip().lower()
        if raw_spam_mode not in {"drop", "tag", "allow"}:
            logger.warning("Invalid spam_filter_mode=%s, fallback to drop", raw_spam_mode)
            raw_spam_mode = "drop"
        self.spam_filter_mode = raw_spam_mode
        raw_duplicate_mode = (duplicate_mode or settings.incremental_duplicate_mode or "drop").strip().lower()
        if raw_duplicate_mode not in {"drop", "tag", "allow"}:
            logger.warning("Invalid duplicate_mode=%s, fallback to drop", raw_duplicate_mode)
            raw_duplicate_mode = "drop"
        self.duplicate_mode = raw_duplicate_mode
        if enable_comments_backfill is None:
            self.comments_backfill_enabled = bool(
                settings.incremental_comments_backfill_enabled
            )
        else:
            self.comments_backfill_enabled = bool(enable_comments_backfill)
        mode_value = (
            settings.incremental_comments_backfill_mode
            if comments_backfill_mode is None
            else comments_backfill_mode
        )
        self.comments_backfill_mode = (mode_value or "smart_shallow").strip()
        max_posts_value = (
            settings.incremental_comments_backfill_max_posts
            if comments_backfill_max_posts is None
            else comments_backfill_max_posts
        )
        self.comments_backfill_max_posts = max(0, int(max_posts_value))
        depth_value = (
            settings.incremental_comments_backfill_depth
            if comments_backfill_depth is None
            else comments_backfill_depth
        )
        self.comments_backfill_depth = max(1, int(depth_value))
        limit_value = (
            settings.incremental_comments_backfill_limit
            if comments_backfill_limit is None
            else comments_backfill_limit
        )
        self.comments_backfill_limit = max(1, min(int(limit_value), 50))
        self.blacklist = None
        try:
            from pathlib import Path
            # Resolve path relative to project root (backend/)
            root_dir = Path(__file__).resolve().parents[2]
            config_path = root_dir / "config" / "community_blacklist.yaml"
            self.blacklist = BlacklistConfig(str(config_path))
        except Exception:
            logger.exception("Failed to load blacklist config; using empty filters")
        from app.core.celery_app import celery_app

        self._runtime_deps: IncrementalRuntimeDeps = build_incremental_runtime_deps(
            IncrementalRuntimeDepsFactoryInput(
                db=self.db,
                send_task=lambda task_name, *args, **kwargs: celery_app.send_task(
                    task_name,
                    *args,
                    **kwargs,
                ),
                comments_backfill_enabled=self.comments_backfill_enabled,
                comments_backfill_max_posts=self.comments_backfill_max_posts,
                comments_backfill_mode=self.comments_backfill_mode,
                comments_backfill_limit=self.comments_backfill_limit,
                comments_backfill_depth=self.comments_backfill_depth,
            )
        )
        self._crawler_runtime = IncrementalCrawlerRuntime(
            IncrementalCrawlerRuntimeInput(
                db=self.db,
                reddit_client=self.reddit_client,
                runtime_deps=self._runtime_deps,
                blacklist=self.blacklist,
                hot_cache_ttl_hours=self.hot_cache_ttl_hours,
                refresh_posts_latest_after_write=self.refresh_posts_latest_after_write,
                source_track=self.source_track,
                crawl_run_id=self.crawl_run_id,
                community_run_id=self.community_run_id,
                spam_filter_mode=self.spam_filter_mode,
                duplicate_mode=self.duplicate_mode,
                spam_classifier=lambda post: self._is_spam_post(post),
                normalize_subreddit_name=normalize_subreddit_name,
                unix_to_datetime=_unix_to_datetime,
                text_norm_hash_available=lambda: _text_norm_hash_available(self.db),
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
                is_current_unique_violation=_is_current_unique_violation,
            )
        )

    def _incremental_crawl_workflow_deps(self):
        return self._crawler_runtime.build_incremental_workflow_deps()

    def _comprehensive_crawl_workflow_deps(self):
        return self._crawler_runtime.build_comprehensive_workflow_deps()

    def _is_spam_post(self, post: RedditPost) -> str | None:
        return self._crawler_runtime.is_spam_post(post)

    def _filter_spam_posts(
        self,
        community_name: str,
        posts: List[RedditPost],
    ) -> List[RedditPost]:
        return self._crawler_runtime.filter_spam_posts(community_name, posts)

    async def _find_content_duplicate(
        self,
        subreddit: str,
        post: RedditPost,
    ) -> str | None:
        return await self._crawler_runtime.find_content_duplicate(subreddit, post)

    async def crawl_community_incremental(
        self,
        community_name: str,
        limit: int = 100,
        time_filter: str = "month",
        sort: str = "top",
    ) -> dict[str, Any]:
        """
        增量抓取单个社区

        Args:
            community_name: 社区名（如 "r/Entrepreneur"）
            limit: 每次抓取的帖子数
            time_filter: 时间范围（week/month/year/all）
            sort: 排序策略（top/new/hot/rising）

        Returns:
            {
                "community": str,
                "new_posts": int,
                "updated_posts": int,
                "duplicates": int,
                "watermark_updated": bool,
            }
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"🔄 开始增量抓取社区: {community_name}")
        workflow_result = await run_incremental_crawl_workflow(
            workflow_input=IncrementalCrawlWorkflowInput(
                community_name=community_name,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
                start_time=start_time,
            ),
            deps=self._incremental_crawl_workflow_deps(),
        )
        payload = workflow_result.payload
        if payload.get("error"):
            logger.error("❌ %s: 抓取失败 - %s", community_name, payload["error"])
        elif payload.get("watermark_updated"):
            logger.info(
                "✅ %s: 新增 %s, 更新 %s, 去重 %s, 耗时 %.2fs",
                community_name,
                payload.get("new_posts", 0),
                payload.get("updated_posts", 0),
                payload.get("duplicates", 0),
                float(payload.get("duration_seconds", 0.0) or 0.0),
            )
        else:
            logger.info("✅ %s: 无新帖子，跳过", community_name)
        return payload

    async def crawl_community_comprehensive(
        self,
        community_name: str,
        time_filter: str = "all",
        max_per_strategy: int = 1000,
        ignore_watermark: bool = True,
    ) -> dict[str, Any]:
        """
        使用多策略抓取单个社区的所有历史数据（top + new + hot）

        Args:
            community_name: 社区名（如 "r/Entrepreneur"）
            time_filter: 时间范围（默认 "all" 抓取所有历史数据）
            max_per_strategy: 每种策略最多抓取的帖子数（默认 1000）
            ignore_watermark: 是否忽略水位线（默认 True，强制重新抓取）

        Returns:
            {
                "community": str,
                "new_posts": int,
                "updated_posts": int,
                "duplicates": int,
                "total_fetched": int,  # 从 API 获取的总帖子数
                "unique_posts": int,   # 去重后的帖子数
                "duration_seconds": float,
            }
        """
        if not self.reddit_client:
            raise ValueError("RedditAPIClient is required for crawling")

        start_time = datetime.now(timezone.utc)
        logger.info(f"🔄 开始多策略抓取社区: {community_name} (time_filter={time_filter})")
        result = await run_comprehensive_crawl_workflow(
            workflow_input=ComprehensiveCrawlWorkflowInput(
                community_name=community_name,
                time_filter=time_filter,
                max_per_strategy=max_per_strategy,
                ignore_watermark=ignore_watermark,
                start_time=start_time,
            ),
            deps=self._comprehensive_crawl_workflow_deps(),
        )
        payload = result.payload
        if payload.get("error"):
            logger.error("❌ %s: 抓取失败 - %s", community_name, payload["error"])
        elif payload.get("unique_posts", 0) == 0:
            logger.info("✅ %s: 无新帖子，跳过", community_name)
        else:
            logger.info(
                "✅ %s: 新增 %s, 更新 %s, 去重 %s, 总获取 %s, 耗时 %.2fs",
                community_name,
                payload.get("new_posts", 0),
                payload.get("updated_posts", 0),
                payload.get("duplicates", 0),
                payload.get("total_fetched", 0),
                float(payload.get("duration_seconds", 0.0) or 0.0),
            )
        return payload

    async def backfill_posts_window(
        self,
        community_name: str,
        *,
        since: datetime,
        until: datetime,
        max_posts: int,
        sort: str = "new",
        after: str | None = None,
    ) -> dict[str, Any]:
        """
        回填帖子（按时间窗切片）。

        口径（Key 已拍板）：
        - 回填只推进 backfill_floor
        - 回填结束后“抬” incremental 水位线到本次真实抓到的 max_seen_created_at
        - 不更新 last_crawled_at（避免影响巡航调度）
        """
        if not self.reddit_client:
            raise ValueError("RedditAPIClient is required for backfill")

        workflow_result = await execute_backfill_posts_workflow(
            workflow_input=BackfillPostsWorkflowInput(
                community_name=community_name,
                since=since,
                until=until,
                max_posts=max_posts,
                sort=sort,
                after=after,
                session=self.db,
                reddit_client=self.reddit_client,
            ),
            deps=BackfillPostsWorkflowDeps(
                dual_write=self._dual_write,
            ),
        )
        return workflow_result.payload

    async def crawl_communities(
        self,
        communities: Iterable[str],
        *,
        limit: int = 100,
        time_filter: str = "month",
        sort: str = "top",
    ) -> list[dict[str, Any]]:
        """
        批量抓取多个社区，顺序调用增量抓取逻辑。

        Returns:
            A list of crawl summaries preserving input order.
        """
        results: list[dict[str, Any]] = []
        for community_name in communities:
            summary = await self.crawl_community_incremental(
                community_name,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
            )
            results.append(summary)
        return results

    async def _get_watermark(self, community_name: str) -> Optional[datetime]:
        """获取社区的水位线（最后抓取的帖子创建时间）"""
        return await self._crawler_runtime.get_watermark(community_name)

    async def _dual_write(
        self,
        community_name: str,
        posts: List[RedditPost],
        trigger_comments_fetch: bool = False,
    ) -> Tuple[int, int, int]:
        """
        双写：先冷库，再热缓存

        Returns:
            (new_count, updated_count, duplicate_count)
        """
        return await self._crawler_runtime.dual_write(
            community_name,
            posts,
            trigger_comments_fetch=trigger_comments_fetch,
        )

    async def ingest_posts_batch(
        self,
        community_name: str,
        posts: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Public helper to persist a batch of posts already fetched externally.

        Performs dual write (cold + hot) and commits once.
        """
        result = await run_ingest_posts_batch(
            workflow_input=IngestPostsBatchInput(
                community_name=community_name,
                posts=posts,
            ),
            deps=IngestPostsBatchDeps(
                execute_dual_write=lambda name, batch: self._dual_write(
                    name,
                    list(batch),
                ),
            ),
        )
        return result.to_payload()

    async def _upsert_to_cold_storage(
        self,
        community_name: str,
        post: RedditPost,
    ) -> Tuple[bool, bool]:
        """
        Upsert 到冷库（posts_raw）

        Returns:
            (is_new, is_updated)
        """
        return await self._crawler_runtime.upsert_to_cold_storage(community_name, post)

    async def _upsert_to_hot_cache(
        self,
        community_name: str,
        post: RedditPost,
    ) -> None:
        """Upsert 到热缓存（posts_hot）"""
        await self._crawler_runtime.upsert_to_hot_cache(community_name, post)

    async def _record_crawl_metrics(
        self,
        successful_crawls: int = 0,
        empty_crawls: int = 0,
        failed_crawls: int = 0,
        total_new_posts: int = 0,
        total_updated_posts: int = 0,
        total_duplicates: int = 0,
        avg_latency_seconds: float = 0.0,
    ) -> None:
        await self._crawler_runtime.record_crawl_metrics(
            successful_crawls=successful_crawls,
            empty_crawls=empty_crawls,
            failed_crawls=failed_crawls,
            total_new_posts=total_new_posts,
            total_updated_posts=total_updated_posts,
            total_duplicates=total_duplicates,
            avg_latency_seconds=avg_latency_seconds,
        )


__all__ = ["IncrementalCrawler"]
