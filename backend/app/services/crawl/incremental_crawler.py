"""
增量抓取服务：冷热双写 + 水位线机制
"""
from __future__ import annotations

import logging
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Tuple

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.community_cache import CommunityCache
from app.models.crawl_metrics import CrawlMetrics
from app.models.posts_storage import PostHot, PostRaw
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.community.community_cache_service import (
    mark_crawl_attempt,
    update_backfill_floor_if_lower,
    update_backfill_cursor,
    update_incremental_waterline_if_forward,
)
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.utils.subreddit import normalize_subreddit_name, subreddit_key
from app.services.community.blacklist_loader import BlacklistConfig
import re

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
        try:
            from pathlib import Path
            # Resolve path relative to project root (backend/)
            root_dir = Path(__file__).resolve().parents[2]
            config_path = root_dir / "config" / "community_blacklist.yaml"
            self.blacklist = BlacklistConfig(str(config_path))
        except Exception:
            logger.exception("Failed to load blacklist config; using empty filters")
            self.blacklist = None

    async def _ensure_author(self, author_id: Optional[str], author_name: Optional[str]) -> None:
        """确保作者存在，避免外键冲突。"""
        if not author_id:
            return

        # 关键修复：使用原子性 UPSERT，不依赖外部会话状态
        stmt = text(
            """
            INSERT INTO authors (author_id, author_name, created_utc, first_seen_at_global)
            VALUES (:aid, :aname, NOW(), NOW())
            ON CONFLICT (author_id) DO NOTHING
            """
        )
        await self.db.execute(stmt, {"aid": author_id, "aname": author_name or author_id})

    def _is_spam_post(self, post: RedditPost) -> str | None:
        """
        垃圾过滤：返回分类标签，None 表示非垃圾。
        """
        text = f"{post.title or ''} {post.selftext or ''}"

        # 作者黑名单
        if self.blacklist and post.author:
            if self.blacklist.is_author_blacklisted(post.author):
                return "Spam_Bot"

        # 硬编码模板
        if post.title == "[placeholder missing post]":
            return "Spam_LowQuality"
        if post.selftext and "Welcome to" in post.selftext and "AmazonFC" in post.selftext:
            return "Spam_Bot"

        # 正则模式
        if self.blacklist and self.blacklist.matches_spam_pattern(text):
            if re.search(r"\b(btc|eth|crypto|token)\b", text, flags=re.IGNORECASE):
                return "Spam_Crypto"
            return "Spam_Ad"

        # 关键词过滤
        if self.blacklist and self.blacklist.should_filter_post(post.title or "", post.selftext or ""):
            return "Spam_LowQuality"

        return None

    def _filter_spam_posts(
        self,
        community_name: str,
        posts: List[RedditPost],
    ) -> List[RedditPost]:
        if self.spam_filter_mode == "allow":
            return posts

        valid_posts: List[RedditPost] = []
        for p in posts:
            spam_category = self._is_spam_post(p)
            if spam_category:
                if self.spam_filter_mode == "drop":
                    logger.warning(
                        "🚫 [SPAM BLOCKED] %s %s in %s: %s...",
                        spam_category,
                        p.id,
                        community_name,
                        (p.title or "")[:40],
                    )
                    continue
                try:
                    setattr(p, "spam_category", spam_category)
                except Exception:
                    # RedditPost uses slots; store in side map for persistence.
                    self._spam_categories[str(p.id)] = spam_category
                logger.warning(
                    "⚠️ [SPAM TAGGED] %s %s in %s: %s...",
                    spam_category,
                    p.id,
                    community_name,
                    (p.title or "")[:40],
                )
            valid_posts.append(p)
        return valid_posts

    async def _find_content_duplicate(
        self,
        subreddit: str,
        post: RedditPost,
    ) -> str | None:
        if not await _text_norm_hash_available(self.db):
            return None
        content = f"{post.title or ''} {post.selftext or ''}".strip()
        if not content:
            return None
        try:
            res = await self.db.execute(
                text(
                    """
                    SELECT source_post_id
                    FROM posts_raw
                    WHERE source = 'reddit'
                      AND subreddit = :subreddit
                      AND text_norm_hash = text_norm_hash(:content)
                    ORDER BY fetched_at DESC
                    LIMIT 1
                    """
                ),
                {"subreddit": subreddit, "content": content},
            )
        except Exception:
            logger.exception("content dedup query failed; skip")
            return None
        row = res.first()
        if row:
            return row[0]
        return None

    def _enqueue_comment_backfill(
        self,
        community_name: str,
        posts: List[RedditPost],
    ) -> None:
        if not self.comments_backfill_enabled or not posts:
            return
        if self.comments_backfill_max_posts <= 0:
            return
        candidates = [p for p in posts if (p.num_comments or 0) > 0]
        if not candidates:
            return
        candidates.sort(key=lambda p: p.num_comments or 0, reverse=True)
        targets = candidates[: self.comments_backfill_max_posts]
        try:
            from app.core.celery_app import celery_app

            for post in targets:
                celery_app.send_task(
                    "comments.fetch_and_ingest",
                    kwargs={
                        "source_post_id": post.id,
                        "subreddit": subreddit_key(community_name),
                        "mode": self.comments_backfill_mode,
                        "limit": self.comments_backfill_limit,
                        "depth": self.comments_backfill_depth,
                    },
                )
        except Exception:
            logger.exception("Failed to dispatch comments.fetch_and_ingest")

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
        if not self.reddit_client:
             raise ValueError("RedditAPIClient is required for crawling")

        start_time = datetime.now(timezone.utc)
        logger.info(f"🔄 开始增量抓取社区: {community_name}")

        # 1. 获取水位线
        watermark = await self._get_watermark(community_name)
        logger.info(f"📍 水位线: last_seen_created_at={watermark}")

        # 2. 抓取新帖子
        raw_name = normalize_subreddit_name(community_name)
        
        # 修正：Reddit API 单次请求 limit 上限为 100
        effective_limit = limit
        if limit > 100:
            logger.warning(f"⚠️ {community_name}: limit {limit} > 100，自动截断为 100 (增量模式)")
            effective_limit = 100
            
        try:
            fetch_result = await self.reddit_client.fetch_subreddit_posts(
                raw_name,
                limit=effective_limit,
                time_filter=time_filter,
                sort=sort,
            )
            # Backward-compatible: allow tests/mocks to return either `posts`
            # or `(posts, next_after)`.
            posts = fetch_result[0] if isinstance(fetch_result, tuple) else fetch_result
        except Exception as e:
            logger.error(f"❌ {community_name}: 抓取失败 - {e}")
            # 记录失败指标并返回失败结果，避免向上抛异常中断调度
            now = datetime.now(timezone.utc)
            await self.db.execute(
                pg_insert(CommunityCache)
                .values(
                    community_name=community_name,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    hit_count=0,
                    crawl_priority=50,
                    crawl_frequency_hours=2,
                    is_active=True,
                    empty_hit=0,
                    success_hit=0,
                    failure_hit=1,
                    avg_valid_posts=0,
                    quality_tier="medium",
                    last_attempt_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["community_name"],
                    set_={
                        "failure_hit": CommunityCache.failure_hit + 1,
                        "last_attempt_at": now,
                    },
                )
            )
            await self.db.commit()
            return {
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
                "error": str(e),
            }

        if not posts:
            logger.warning(f"⚠️ {community_name}: 未抓取到任何帖子")
            # 计入 empty_hit
            now = datetime.now(timezone.utc)
            await self.db.execute(
                pg_insert(CommunityCache)
                .values(
                    community_name=community_name,
                    last_crawled_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["community_name"],
                    set_={
                        "empty_hit": CommunityCache.empty_hit + 1,
                        "last_crawled_at": now,
                    },
                )
            )
            await self.db.commit()

            # T1.4 埋点：记录空结果
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self._record_crawl_metrics(
                empty_crawls=1,
                avg_latency_seconds=duration,
            )

            return {
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
            }

        # 3. 过滤：只保留新于水位线的帖子
        if watermark:
            posts = [p for p in posts if _unix_to_datetime(p.created_utc) > watermark]
            logger.info(f"🔍 过滤后剩余 {len(posts)} 条新帖子（水位线之后）")

        # 3.1 垃圾分类过滤
        posts = self._filter_spam_posts(community_name, posts)

        if not posts:
            logger.info(f"✅ {community_name}: 无新帖子，跳过")
            return {
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "watermark_updated": False,
            }

        # 4. 双写：先冷库，再热缓存
        new_count, updated_count, dup_count = await self._dual_write(
            community_name, posts, trigger_comments_fetch=True
        )
        # 4.1 有新增则触发打分任务（rulebook_v1）
        if new_count:
            try:
                from app.core.celery_app import celery_app

                celery_app.send_task(
                    "tasks.analysis.score_new_posts_v1",
                    kwargs={"limit": max(200, new_count + 50)},
                )
            except Exception:
                logger.exception("Failed to dispatch score_new_posts_v1 after crawl")

        # 5. 更新水位线
        latest_post = max(posts, key=lambda p: p.created_utc)
        await self._update_watermark(
            community_name,
            latest_post.id,
            _unix_to_datetime(latest_post.created_utc),
            total_fetched=len(posts),
            new_valid_posts=new_count,
            dedup_rate=(dup_count / len(posts) * 100) if posts else 0,
        )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ {community_name}: 新增 {new_count}, 更新 {updated_count}, "
            f"去重 {dup_count}, 耗时 {duration:.2f}s"
        )

        # T1.4 埋点：记录成功抓取
        await self._record_crawl_metrics(
            successful_crawls=1,
            total_new_posts=new_count,
            total_updated_posts=updated_count,
            total_duplicates=dup_count,
            avg_latency_seconds=duration,
        )

        return {
            "community": community_name,
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "watermark_updated": True,
            "duration_seconds": duration,
        }

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

        # 1. 获取水位线（如果不忽略）
        watermark = None if ignore_watermark else await self._get_watermark(community_name)
        if watermark:
            logger.info(f"📍 水位线: last_seen_created_at={watermark}")
        else:
            logger.info(f"📍 忽略水位线，抓取所有历史数据")

        # 2. 使用多策略抓取
        raw_name = (
            community_name[2:]
            if community_name.lower().startswith("r/")
            else community_name
        )

        try:
            posts = await self.reddit_client.fetch_comprehensive_posts(
                raw_name,
                time_filter=time_filter,
                max_per_strategy=max_per_strategy,
            )
            total_fetched = len(posts)
            logger.info(f"📥 {community_name}: 获取 {total_fetched} 个不重复帖子")
        except Exception as e:
            logger.error(f"❌ {community_name}: 抓取失败 - {e}")
            return {
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "total_fetched": 0,
                "unique_posts": 0,
                "duration_seconds": 0,
                "error": str(e),
            }

        # 3. 过滤：只保留新于水位线的帖子（如果有水位线）
        if watermark:
            posts = [p for p in posts if _unix_to_datetime(p.created_utc) > watermark]
            logger.info(f"🔍 过滤后剩余 {len(posts)} 条新帖子（水位线之后）")

        # 3.1 垃圾分类过滤
        posts = self._filter_spam_posts(community_name, posts)

        if not posts:
            logger.info(f"✅ {community_name}: 无新帖子，跳过")
            return {
                "community": community_name,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "total_fetched": total_fetched,
                "unique_posts": 0,
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }

        # 4. 写入数据库（冷库 + 热缓存）
        new_count, updated_count, dup_count = await self._dual_write(
            community_name, posts
        )

        # 5. 更新水位线
        latest_post = max(posts, key=lambda p: p.created_utc)
        await self._update_watermark(
            community_name,
            latest_post.id,
            _unix_to_datetime(latest_post.created_utc),
            total_fetched=total_fetched,
            new_valid_posts=new_count,
            dedup_rate=(dup_count / len(posts) * 100) if posts else 0,
        )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ {community_name}: 新增 {new_count}, 更新 {updated_count}, "
            f"去重 {dup_count}, 总获取 {total_fetched}, 耗时 {duration:.2f}s"
        )

        return {
            "community": community_name,
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "total_fetched": total_fetched,
            "unique_posts": len(posts),
            "duration_seconds": duration,
        }

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

        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if since >= until:
            raise ValueError("since must be < until")

        start_time = datetime.now(timezone.utc)
        norm = normalize_subreddit_name(community_name)
        planned_max_posts = max(1, int(max_posts))
        max_pages = max(0, int(os.getenv("BACKFILL_MAX_PAGES_PER_RUN", "0")))
        max_seconds = max(0, int(os.getenv("BACKFILL_MAX_SECONDS_PER_RUN", "0")))
        posts: list[RedditPost] = []
        cursor_before = after
        cursor_created_before: datetime | None = None
        try:
            row = await self.db.execute(
                text(
                    """
                    SELECT backfill_cursor, backfill_cursor_created_at
                    FROM community_cache
                    WHERE community_name = :name
                    """
                ),
                {"name": norm},
            )
            existing = row.first()
            if existing:
                existing_cursor = existing[0]
                existing_created = existing[1]
                if cursor_before is None:
                    cursor_before = existing_cursor
                cursor_created_before = existing_created
        except Exception:
            cursor_created_before = None

        cursor_after = cursor_before
        truncated = False
        truncated_reason: str | None = None
        pages_processed = 0
        api_calls_total = 0
        items_api_returned = 0
        items_after_window = 0
        items_skipped_outside_window_newer = 0
        items_skipped_outside_window_older = 0
        items_skipped_missing_created_at = 0
        last_batch_min_created: datetime | None = None
        stop_reason: str | None = None

        while len(posts) < planned_max_posts:
            batch_limit = min(100, planned_max_posts - len(posts))
            try:
                batch, next_after = await self.reddit_client.fetch_subreddit_posts(
                    norm,
                    limit=batch_limit,
                    time_filter="all",
                    sort=sort,
                    after=cursor_after,
                )
            except Exception:
                await mark_crawl_attempt(norm, session=self.db)
                raise

            api_calls_total += 1

            if not batch:
                cursor_after = None
                stop_reason = "no_more_pages"
                break

            pages_processed += 1
            items_api_returned += len(batch)
            batch_created = [
                _unix_to_datetime(p.created_utc) for p in batch if p.created_utc is not None
            ]
            if batch_created:
                last_batch_min_created = min(batch_created)
                last_batch_max_created = max(batch_created)
                if (
                    cursor_created_before is None
                    or last_batch_max_created > cursor_created_before
                ):
                    cursor_created_before = last_batch_max_created
                await update_backfill_cursor(
                    norm,
                    cursor_after=next_after,
                    cursor_created_at=last_batch_min_created,
                    session=self.db,
                )

            hit_floor = False
            for p in batch:
                created_at = _unix_to_datetime(p.created_utc)
                if created_at is None:
                    items_skipped_missing_created_at += 1
                    continue
                if created_at >= until:
                    items_skipped_outside_window_newer += 1
                    continue
                if created_at < since:
                    hit_floor = True
                    items_skipped_outside_window_older += 1
                    break
                posts.append(p)
                items_after_window += 1
                if len(posts) >= planned_max_posts:
                    break

            if len(posts) >= planned_max_posts:
                truncated = bool(next_after)
                truncated_reason = "cursor_remaining" if truncated else None
                cursor_after = next_after if truncated else None
                if truncated_reason:
                    stop_reason = truncated_reason
                break
            if max_pages > 0 and pages_processed >= max_pages:
                truncated = bool(next_after)
                truncated_reason = "budget_remaining" if truncated else None
                cursor_after = next_after if truncated else None
                if truncated_reason:
                    stop_reason = truncated_reason
                break
            if max_seconds > 0:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= max_seconds:
                    truncated = bool(next_after)
                    truncated_reason = "budget_remaining" if truncated else None
                    cursor_after = next_after if truncated else None
                    if truncated_reason:
                        stop_reason = truncated_reason
                    break
            if hit_floor:
                cursor_after = None
                stop_reason = "floor_reached"
                break
            if not next_after:
                cursor_after = None
                stop_reason = "no_more_pages"
                break
            cursor_after = next_after

        if not posts:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            status = "completed"
            reason = None
            if stop_reason in {"budget_remaining", "cursor_remaining"}:
                status = "partial"
                reason = stop_reason
            return {
                "community": norm,
                "status": status,
                "reason": reason,
                "stop_reason": stop_reason,
                "metrics_schema_version": 2,
                "plan_kind": "backfill_posts",
                "window_since": since.isoformat(),
                "window_until": until.isoformat(),
                "total_fetched": 0,
                "unique_posts": 0,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "api_calls_total": api_calls_total,
                "items_api_returned": items_api_returned,
                "items_after_window": items_after_window,
                "items_skipped_outside_window_newer": items_skipped_outside_window_newer,
                "items_skipped_outside_window_older": items_skipped_outside_window_older,
                "items_skipped_missing_created_at": items_skipped_missing_created_at,
                "items_new": 0,
                "items_updated": 0,
                "items_duplicate": 0,
                "items_written_posts_inserted": 0,
                "items_written_posts_updated": 0,
                "items_written_posts_total": 0,
                "pages_processed": pages_processed,
                "duration_seconds": duration,
                "max_seen_created_at": None,
                "min_seen_created_at": None,
                "cursor_before": cursor_before,
                "cursor_after": cursor_after,
                "cursor_created_before": (
                    cursor_created_before.isoformat()
                    if cursor_created_before is not None
                    else None
                ),
                "cursor_created_after": (
                    last_batch_min_created.isoformat()
                    if last_batch_min_created is not None
                    else None
                ),
            }

        new_count, updated_count, dup_count = await self._dual_write(
            norm, posts, trigger_comments_fetch=False
        )

        max_post = max(posts, key=lambda p: p.created_utc)
        min_post = min(posts, key=lambda p: p.created_utc)
        max_seen = _unix_to_datetime(max_post.created_utc)
        min_seen = _unix_to_datetime(min_post.created_utc)

        await update_backfill_floor_if_lower(
            norm, backfill_floor=min_seen, session=self.db
        )
        await update_incremental_waterline_if_forward(
            norm,
            last_seen_post_id=max_post.id,
            last_seen_created_at=max_seen,
            session=self.db,
        )
        await self.db.commit()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        hit_posts_limit = len(posts) >= planned_max_posts
        return {
            "community": norm,
            "status": "partial" if truncated else "completed",
            "reason": truncated_reason if truncated else None,
            "stop_reason": truncated_reason or stop_reason,
            "metrics_schema_version": 2,
            "plan_kind": "backfill_posts",
            "window_since": since.isoformat(),
            "window_until": until.isoformat(),
            "total_fetched": len(posts),
            "unique_posts": len(posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "api_calls_total": api_calls_total,
            "items_api_returned": items_api_returned,
            "items_after_window": items_after_window,
            "items_skipped_outside_window_newer": items_skipped_outside_window_newer,
            "items_skipped_outside_window_older": items_skipped_outside_window_older,
            "items_skipped_missing_created_at": items_skipped_missing_created_at,
            "items_new": new_count,
            "items_updated": updated_count,
            "items_duplicate": dup_count,
            "items_written_posts_inserted": new_count,
            "items_written_posts_updated": updated_count,
            "items_written_posts_total": new_count + updated_count,
            "pages_processed": pages_processed,
            "hit_posts_limit": hit_posts_limit,
            "duration_seconds": duration,
            "max_seen_created_at": max_seen.isoformat(),
            "min_seen_created_at": min_seen.isoformat(),
            "cursor_after": cursor_after,
            "cursor_before": cursor_before,
            "cursor_created_before": (
                cursor_created_before.isoformat() if cursor_created_before is not None else None
            ),
            "cursor_created_after": (
                last_batch_min_created.isoformat()
                if last_batch_min_created is not None
                else None
            ),
        }

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
        result = await self.db.execute(
            select(CommunityCache.last_seen_created_at).where(
                CommunityCache.community_name == community_name
            )
        )
        row = result.scalar_one_or_none()
        return row if row else None

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
        new_count = 0
        updated_count = 0
        dup_count = 0
        
        # 收集新增帖子，用于增量回填评论
        new_posts_for_comments: List[RedditPost] = []

        # Ensure an outer transaction exists before SAVEPOINT (begin_nested).
        if not self.db.in_transaction():
            await self.db.begin()

        # 先全部写冷库，单独提交，确保冷数据即使热缓存失败也能落库
        for post in posts:
            try:
                async with self.db.begin_nested():
                    is_new, is_updated = await self._upsert_to_cold_storage(
                        community_name, post
                    )
            except IntegrityError as exc:
                if _is_current_unique_violation(exc):
                    dup_count += 1
                    logger.info(
                        "♻️ Post %s current-unique conflict; skip",
                        post.id,
                    )
                    continue
                raise

            if is_new:
                new_count += 1
                new_posts_for_comments.append(post)
            elif is_updated:
                updated_count += 1
            else:
                dup_count += 1

        try:
            await self.db.flush()
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("❌ 冷库提交失败，已回滚（community=%s）", community_name)
            raise

        # 热缓存最佳努力：单独事务，失败不影响冷库
        for post in posts:
            try:
                await self._upsert_to_hot_cache(community_name, post)
            except Exception:
                await self.db.rollback()
                logger.exception("⚠️ 热缓存写入失败，已跳过（post=%s, community=%s）", post.id, community_name)
            else:
                try:
                    await self.db.commit()
                except Exception:
                    await self.db.rollback()
                    logger.exception("⚠️ 热缓存提交失败，已回滚（post=%s, community=%s）", post.id, community_name)

        if self.refresh_posts_latest_after_write and (new_count or updated_count):
            self._schedule_posts_latest_refresh()

        if trigger_comments_fetch:
            self._enqueue_comment_backfill(community_name, new_posts_for_comments)

        return new_count, updated_count, dup_count

    async def ingest_posts_batch(
        self,
        community_name: str,
        posts: List[RedditPost],
    ) -> dict[str, int]:
        """Public helper to persist a batch of posts already fetched externally.

        Performs dual write (cold + hot) and commits once.
        """
        if not posts:
            return {"new": 0, "updated": 0, "duplicates": 0}
        new_count = 0
        updated_count = 0
        dup_count = 0
        post_objects = []
        for p_dict in posts:
            post_obj = RedditPost(
                id=p_dict.get("id"),
                title=p_dict.get("title"),
                selftext=p_dict.get("selftext"),
                score=p_dict.get("score"),
                num_comments=p_dict.get("num_comments"),
                created_utc=float(p_dict.get("created_utc", 0)),
                author=p_dict.get("author"),
                url=p_dict.get("url"),
                permalink=p_dict.get("permalink"),
                subreddit=p_dict.get("subreddit"),
            )
            post_objects.append(post_obj)

        for post in post_objects:
            is_new, is_updated = await self._upsert_to_cold_storage(community_name, post)
            if is_new:
                new_count += 1
            elif is_updated:
                updated_count += 1
            else:
                dup_count += 1
            await self._upsert_to_hot_cache(community_name, post)

        try:
            await self.db.flush()
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("❌ 批量入库提交失败，已回滚（community=%s）", community_name)
            raise
        if self.refresh_posts_latest_after_write and (new_count or updated_count):
            self._schedule_posts_latest_refresh()
        return {"new": new_count, "updated": updated_count, "duplicates": dup_count}

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
        now = datetime.now(timezone.utc)
        created_at = _unix_to_datetime(post.created_utc)

        # 确保作者存在；若作者为空则不写外键以避免 FK 冲突
        if post.author:
            await self._ensure_author(post.author, post.author)
            author_id = post.author
            author_name = post.author
        else:
            author_id = None
            author_name = None

        # 查询最新版本（不依赖 is_current，避免标志异常导致误判）
        existing_row = await self.db.execute(
            text(
                """
                SELECT id, version, score, num_comments, title, body, is_current
                FROM posts_raw
                WHERE source = 'reddit' AND source_post_id = :pid
                ORDER BY version DESC
                LIMIT 1
                """
            ),
            {"pid": post.id},
        )
        existing_post = existing_row.mappings().first()

        # 基础字段：统一使用规范化的 subreddit key 以便与 comments/统计逻辑对齐
        norm_sub = subreddit_key(community_name)
        base_values: dict[str, Any] = {
            "source": "reddit",
            "source_post_id": post.id,
            "created_at": created_at,
            "fetched_at": now,
            "first_seen_at": now,
            "source_track": self.source_track,
            "author_id": author_id,
            "author_name": author_name,
            "title": post.title,
            "body": post.selftext or "",
            "url": post.url,
            "subreddit": norm_sub,
            "score": post.score,
            "num_comments": post.num_comments,
            "is_current": True,
            "valid_from": now,
            "spam_category": getattr(post, "spam_category", None),
        }

        has_run_col = await _posts_raw_has_crawl_run_id(self.db)
        include_run_id = bool(has_run_col and self.crawl_run_id)
        has_community_run_col = await _posts_raw_has_community_run_id(self.db)
        include_community_run_id = bool(has_community_run_col and self.community_run_id)

        if include_run_id and self.crawl_run_id and not self._crawler_run_row_ensured:
            await ensure_crawler_run(
                self.db,
                crawl_run_id=self.crawl_run_id,
                config={"mode": "incremental", "source_track": self.source_track},
            )
            self._crawler_run_row_ensured = True
        if include_run_id and self.crawl_run_id:
            base_values["crawl_run_id"] = self.crawl_run_id
        if include_community_run_id and self.community_run_id:
            base_values["community_run_id"] = self.community_run_id

        metadata_payload = {
            "permalink": post.permalink,
            "upvote_ratio": getattr(post, "upvote_ratio", None),
        }
        spam_category = getattr(post, "spam_category", None)
        if not spam_category:
            spam_category = self._spam_categories.get(str(post.id))
        if spam_category:
            metadata_payload["spam_category"] = spam_category
        if self.crawl_run_id:
            metadata_payload["run_id"] = self.crawl_run_id
        if self.community_run_id:
            metadata_payload["community_run_id"] = self.community_run_id

        if existing_post is None:
            duplicate_of = None
            is_duplicate = False
            if self.duplicate_mode != "allow":
                duplicate_of = await self._find_content_duplicate(norm_sub, post)
            if duplicate_of:
                if self.duplicate_mode == "drop":
                    logger.info(
                        "♻️ Post %s content-duplicate of %s in %s, skip insert",
                        post.id,
                        duplicate_of,
                        norm_sub,
                    )
                    return False, False
                metadata_payload["duplicate_of"] = duplicate_of
                metadata_payload["is_duplicate"] = True
                is_duplicate = True
            # 新帖子：version=1，冲突则刷新 fetched_at（不抛异常）
            extra_columns = ""
            extra_values = ""
            if include_run_id:
                extra_columns += ", crawl_run_id"
                extra_values += ", :crawl_run_id"
            if include_community_run_id:
                extra_columns += ", community_run_id"
                extra_values += ", :community_run_id"
            sql = text(
                f"""
                INSERT INTO posts_raw (
                    source, source_post_id, version, edit_count,
                    created_at, fetched_at, first_seen_at, source_track,
                    author_id, author_name,
                    title, body, url, subreddit, score, num_comments,
                    is_current, valid_from, valid_to, metadata{extra_columns}
                ) VALUES (
                    :source, :source_post_id, 1, 0,
                    :created_at, :fetched_at, :first_seen_at, :source_track,
                    :author_id, :author_name,
                    :title, :body, :url, :subreddit, :score, :num_comments,
                    TRUE, :valid_from, '9999-12-31'::timestamptz, :metadata{extra_values}
                )
                ON CONFLICT (source, source_post_id, version)
                DO UPDATE SET fetched_at = EXCLUDED.fetched_at
                """
            )
            params = {
                **base_values,
                "valid_to": None,
                "metadata": json.dumps(metadata_payload),
            }
            await self.db.execute(sql, params)
            return (not is_duplicate), False

        # 已存在：检查是否需要新版本
        body_text = post.selftext or ""
        has_changes = any(
            [
                existing_post["score"] != post.score,
                existing_post["num_comments"] != post.num_comments,
                existing_post["title"] != post.title,
                (existing_post["body"] or "") != body_text,
            ]
        )

        if not has_changes:
            # 无内容变更，刷新 fetched_at，保持 is_current
            logger.info(f"♻️ Post {post.id}: No content changes. Updating fetched_at to {now}")
            extra_columns = ""
            extra_values = ""
            if include_run_id:
                extra_columns += ", crawl_run_id"
                extra_values += ", :crawl_run_id"
            if include_community_run_id:
                extra_columns += ", community_run_id"
                extra_values += ", :community_run_id"
            await self.db.execute(
                text(
                    f"""
                    INSERT INTO posts_raw (
                        source, source_post_id, version, edit_count,
                        created_at, fetched_at, first_seen_at, source_track,
                        author_id, author_name,
                        title, body, url, subreddit, score, num_comments,
                        is_current, valid_from, valid_to, metadata{extra_columns}
                    ) VALUES (
                        :source, :source_post_id, :version, :edit_count,
                        :created_at, :fetched_at, :first_seen_at, :source_track,
                        :author_id, :author_name,
                        :title, :body, :url, :subreddit, :score, :num_comments,
                        TRUE, :valid_from, '9999-12-31'::timestamptz, :metadata{extra_values}
                    )
                    ON CONFLICT (source, source_post_id, version)
                    DO UPDATE SET fetched_at = EXCLUDED.fetched_at
                    """
                ),
                {
                    **base_values,
                    "version": existing_post["version"],
                    "edit_count": 0,
                    "metadata": json.dumps(metadata_payload),
                },
            )
            return False, False

        # 关闭旧版本（若存在）
        await self.db.execute(
            text(
                """
                UPDATE posts_raw
                SET is_current = FALSE, valid_to = :valid_to
                WHERE source = 'reddit' AND source_post_id = :pid AND is_current = TRUE
                """
            ),
            {"valid_to": now, "pid": post.id},
        )

        # 插入新版本
        # 取最大版本号再 +1，避免重复版本冲突
        max_version_row = await self.db.execute(
            select(func.max(PostRaw.version)).where(
                PostRaw.source == "reddit",
                PostRaw.source_post_id == post.id,
            )
        )
        next_version = (max_version_row.scalar() or 0) + 1
        extra_columns = ""
        extra_values = ""
        extra_update = ""
        if include_run_id:
            extra_columns += ", crawl_run_id"
            extra_values += ", :crawl_run_id"
            extra_update += ", crawl_run_id = EXCLUDED.crawl_run_id"
        if include_community_run_id:
            extra_columns += ", community_run_id"
            extra_values += ", :community_run_id"
            extra_update += ", community_run_id = EXCLUDED.community_run_id"
        insert_sql = text(
            f"""
            INSERT INTO posts_raw (
                source, source_post_id, version, edit_count,
                created_at, fetched_at, first_seen_at, source_track,
                author_id, author_name,
                title, body, url, subreddit, score, num_comments,
                is_current, valid_from, valid_to, metadata{extra_columns}
            ) VALUES (
                :source, :source_post_id, :version, :edit_count,
                :created_at, :fetched_at, :first_seen_at, :source_track,
                :author_id, :author_name,
                :title, :body, :url, :subreddit, :score, :num_comments,
                TRUE, :valid_from, '9999-12-31'::timestamptz, :metadata{extra_values}
            )
            ON CONFLICT (source, source_post_id, version)
            DO UPDATE SET
                fetched_at = EXCLUDED.fetched_at,
                is_current = EXCLUDED.is_current,
                valid_from = EXCLUDED.valid_from,
                valid_to = EXCLUDED.valid_to,
                edit_count = EXCLUDED.edit_count,
                score = EXCLUDED.score,
                num_comments = EXCLUDED.num_comments,
                title = EXCLUDED.title,
                body = EXCLUDED.body,
                metadata = EXCLUDED.metadata{extra_update}
            """
        )
        params = {
            **base_values,
            "version": next_version,
            "edit_count": (existing_post.get("edit_count") or 0) + 1 if isinstance(existing_post, dict) else (getattr(existing_post, "edit_count", 0) or 0) + 1,
            "metadata": json.dumps(metadata_payload),
        }
        await self.db.execute(insert_sql, params)
        return False, True  # (is_new=False, is_updated=True)

    async def _upsert_to_hot_cache(
        self,
        community_name: str,
        post: RedditPost,
    ) -> None:
        """Upsert 到热缓存（posts_hot）"""
        # Failsafe: ensure author here too in case called independently
        await self._ensure_author(post.author, post.author)

        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self.hot_cache_ttl_hours
        )

        norm_sub = subreddit_key(community_name)

        base_values = dict(
            source="reddit",
            source_post_id=post.id,
            created_at=_unix_to_datetime(post.created_utc),
            cached_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            author_id=post.author,
            author_name=post.author,
            title=post.title,
            body=post.selftext or "",
            subreddit=norm_sub,
            score=post.score,
            num_comments=post.num_comments,
        )

        # 注意：对于 metadata 列，使用 PostHot.extra_data（Python 属性名）
        # SQLAlchemy 会自动映射到数据库列 "metadata"
        # subreddit 同样统一为 canonical key，保证 posts_raw/posts_hot/comments 之间一致
        stmt = pg_insert(PostHot).values(
            **base_values,
            **{PostHot.extra_data.key: {"permalink": post.permalink}},
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "source_post_id"],
            set_={
                "cached_at": stmt.excluded.cached_at,
                "expires_at": stmt.excluded.expires_at,
                "author_id": stmt.excluded.author_id,
                "author_name": stmt.excluded.author_name,
                "score": stmt.excluded.score,
                "num_comments": stmt.excluded.num_comments,
                "title": stmt.excluded.title,
                "body": stmt.excluded.body,
                "metadata": stmt.excluded.metadata,
            },
        )

        try:
            await self.db.execute(stmt)
        except Exception as exc:
            # 若数据库缺少 (source, source_post_id) 唯一约束，则回退为查询 + 覆盖更新
            if "no unique or exclusion constraint" not in str(exc):
                raise

            await self.db.rollback()

            existing = await self.db.execute(
                select(PostHot).where(
                    PostHot.source == "reddit",
                    PostHot.source_post_id == post.id,
                )
            )
            row = existing.scalars().first()
            if row:
                await self.db.execute(
                    update(PostHot)
                    .where(PostHot.id == row.id)
                    .values(
                        **base_values,
                        **{PostHot.extra_data.key: {"permalink": post.permalink}},
                    )
                )
            else:
                await self.db.execute(
                    pg_insert(PostHot).values(
                        **base_values,
                        **{PostHot.extra_data.key: {"permalink": post.permalink}},
                    )
                )

    def _schedule_posts_latest_refresh(self) -> None:
        """调度 posts_latest 刷新任务，避免阻塞抓取事务。"""
        try:
            from app.core.celery_app import celery_app

            celery_app.send_task("tasks.maintenance.refresh_posts_latest")
        except Exception:  # pragma: no cover - 调度失败时仅记录日志
            logger.exception("Failed to schedule posts_latest refresh task")

    async def _update_watermark(
        self,
        community_name: str,
        last_seen_post_id: str,
        last_seen_created_at: datetime,
        total_fetched: int,
        new_valid_posts: int,
        dedup_rate: float,
    ) -> None:
        """更新水位线"""
        await self.db.execute(
            pg_insert(CommunityCache)
            .values(
                community_name=community_name,
                quality_tier="medium",
                last_seen_post_id=last_seen_post_id,
                last_seen_created_at=last_seen_created_at,
                total_posts_fetched=total_fetched,
                dedup_rate=dedup_rate,
                last_crawled_at=datetime.now(timezone.utc),
                success_hit=1,
                avg_valid_posts=new_valid_posts,
            )
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "last_seen_post_id": last_seen_post_id,
                    "last_seen_created_at": last_seen_created_at,
                    "total_posts_fetched": CommunityCache.total_posts_fetched
                    + total_fetched,
                    "dedup_rate": dedup_rate,
                    "last_crawled_at": datetime.now(timezone.utc),
                    "success_hit": CommunityCache.success_hit + 1,
                    "avg_valid_posts": new_valid_posts,
                    "quality_tier": CommunityCache.quality_tier,
                },
            )
        )
        await self.db.commit()

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
        """
        记录抓取指标到 crawl_metrics 表（T1.4 埋点）

        每小时汇总一次，记录当前小时的抓取统计
        """
        now = datetime.now(timezone.utc)
        metric_date = now.date()
        metric_hour = now.hour

        # 查询当前小时的 valid_posts_24h（从 posts_hot 表）
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(PostHot.source_post_id)).where(
                PostHot.cached_at >= now - timedelta(hours=24)
            )
        )
        valid_posts_24h = result.scalar() or 0

        # 查询活跃社区总数
        result = await self.db.execute(
            select(func.count(CommunityCache.community_name)).where(
                CommunityCache.is_active == True  # noqa: E712
            )
        )
        total_communities = result.scalar() or 0

        # 计算缓存命中率（去重率的倒数）
        total_posts = total_new_posts + total_updated_posts + total_duplicates
        cache_hit_rate = (
            (total_duplicates / total_posts * 100) if total_posts > 0 else 0.0
        )

        # Upsert 到 crawl_metrics 表
        stmt = pg_insert(CrawlMetrics).values(
            metric_date=metric_date,
            metric_hour=metric_hour,
            cache_hit_rate=cache_hit_rate,
            valid_posts_24h=valid_posts_24h,
            total_communities=total_communities,
            successful_crawls=successful_crawls,
            empty_crawls=empty_crawls,
            failed_crawls=failed_crawls,
            avg_latency_seconds=avg_latency_seconds,
            total_new_posts=total_new_posts,
            total_updated_posts=total_updated_posts,
            total_duplicates=total_duplicates,
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_crawl_metrics_date_hour",
            set_={
                "cache_hit_rate": cache_hit_rate,
                "valid_posts_24h": valid_posts_24h,
                "total_communities": total_communities,
                "successful_crawls": CrawlMetrics.successful_crawls + successful_crawls,
                "empty_crawls": CrawlMetrics.empty_crawls + empty_crawls,
                "failed_crawls": CrawlMetrics.failed_crawls + failed_crawls,
                "avg_latency_seconds": avg_latency_seconds,
                "total_new_posts": CrawlMetrics.total_new_posts + total_new_posts,
                "total_updated_posts": CrawlMetrics.total_updated_posts + total_updated_posts,
                "total_duplicates": CrawlMetrics.total_duplicates + total_duplicates,
            },
        )

        await self.db.execute(stmt)
        await self.db.commit()

        logger.info(
            f"📊 埋点记录: {metric_date} {metric_hour}:00 - "
            f"成功={successful_crawls}, 空结果={empty_crawls}, 失败={failed_crawls}, "
            f"新增={total_new_posts}, 更新={total_updated_posts}, 去重={total_duplicates}"
        )


__all__ = ["IncrementalCrawler"]
