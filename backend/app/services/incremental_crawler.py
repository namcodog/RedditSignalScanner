"""
增量抓取服务：冷热双写 + 水位线机制
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posts_storage import PostRaw, PostHot
from app.models.community_cache import CommunityCache
from app.services.reddit_client import RedditPost, RedditAPIClient

logger = logging.getLogger(__name__)


def _unix_to_datetime(unix_timestamp: float) -> datetime:
    """将 Unix 时间戳转换为 UTC datetime"""
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)


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
        reddit_client: RedditAPIClient,
        hot_cache_ttl_hours: int = 24,
    ):
        self.db = db
        self.reddit_client = reddit_client
        self.hot_cache_ttl_hours = hot_cache_ttl_hours
    
    async def crawl_community_incremental(
        self,
        community_name: str,
        limit: int = 100,
        time_filter: str = "month",
    ) -> dict:
        """
        增量抓取单个社区
        
        Args:
            community_name: 社区名（如 "r/Entrepreneur"）
            limit: 每次抓取的帖子数
            time_filter: 时间范围（week/month）
        
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
        
        # 1. 获取水位线
        watermark = await self._get_watermark(community_name)
        logger.info(f"📍 水位线: last_seen_created_at={watermark}")
        
        # 2. 抓取新帖子
        raw_name = community_name[2:] if community_name.lower().startswith("r/") else community_name
        posts = await self.reddit_client.fetch_subreddit_posts(
            raw_name,
            limit=limit,
            time_filter=time_filter,
            sort="top",
        )
        
        if not posts:
            logger.warning(f"⚠️ {community_name}: 未抓取到任何帖子")
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
            community_name, posts
        )
        
        # 5. 更新水位线
        latest_post = max(posts, key=lambda p: p.created_utc)
        await self._update_watermark(
            community_name,
            latest_post.id,
            _unix_to_datetime(latest_post.created_utc),
            total_fetched=len(posts),
            dedup_rate=(dup_count / len(posts) * 100) if posts else 0,
        )
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ {community_name}: 新增 {new_count}, 更新 {updated_count}, "
            f"去重 {dup_count}, 耗时 {duration:.2f}s"
        )
        
        return {
            "community": community_name,
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "watermark_updated": True,
            "duration_seconds": duration,
        }
    
    async def _get_watermark(self, community_name: str) -> Optional[datetime]:
        """获取社区的水位线（最后抓取的帖子创建时间）"""
        result = await self.db.execute(
            select(CommunityCache.last_seen_created_at)
            .where(CommunityCache.community_name == community_name)
        )
        row = result.scalar_one_or_none()
        return row if row else None
    
    async def _dual_write(
        self,
        community_name: str,
        posts: List[RedditPost],
    ) -> Tuple[int, int, int]:
        """
        双写：先冷库，再热缓存
        
        Returns:
            (new_count, updated_count, duplicate_count)
        """
        new_count = 0
        updated_count = 0
        dup_count = 0
        
        for post in posts:
            # 1. 写入冷库（增量 upsert）
            is_new, is_updated = await self._upsert_to_cold_storage(community_name, post)
            
            if is_new:
                new_count += 1
            elif is_updated:
                updated_count += 1
            else:
                dup_count += 1
            
            # 2. 写入热缓存（覆盖式）
            await self._upsert_to_hot_cache(community_name, post)
        
        # 提交事务
        await self.db.commit()
        
        return new_count, updated_count, dup_count
    
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
        # 构造 upsert 语句
        stmt = pg_insert(PostRaw).values(
            source="reddit",
            source_post_id=post.id,
            version=1,
            created_at=_unix_to_datetime(post.created_utc),
            fetched_at=datetime.now(timezone.utc),
            author_id=post.author,
            author_name=post.author,
            title=post.title,
            body=post.selftext or "",
            url=post.url,
            subreddit=community_name,
            score=post.score,
            num_comments=post.num_comments,
            extra_data={
                "permalink": post.permalink,
                "upvote_ratio": getattr(post, "upvote_ratio", None),
            },
        )

        # ON CONFLICT: 如果已存在，检查是否需要更新版本
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "source_post_id", "version"],
            set_={
                "score": stmt.excluded.score,
                "num_comments": stmt.excluded.num_comments,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        
        # 执行并返回是否新增/更新
        # 注意：这里简化处理，实际应该检查 text_norm_hash 判断是否编辑
        await self.db.execute(stmt)
        
        # TODO: 实现 SCD2 版本追踪（检测编辑）
        return True, False  # 暂时返回 (is_new=True, is_updated=False)
    
    async def _upsert_to_hot_cache(
        self,
        community_name: str,
        post: RedditPost,
    ) -> None:
        """Upsert 到热缓存（posts_hot）"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.hot_cache_ttl_hours)
        
        stmt = pg_insert(PostHot).values(
            source="reddit",
            source_post_id=post.id,
            created_at=_unix_to_datetime(post.created_utc),
            cached_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            title=post.title,
            body=post.selftext or "",
            subreddit=community_name,
            score=post.score,
            num_comments=post.num_comments,
            extra_data={
                "permalink": post.permalink,
            },
        )

        # ON CONFLICT: 覆盖式更新
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "source_post_id"],
            set_={
                "cached_at": stmt.excluded.cached_at,
                "expires_at": stmt.excluded.expires_at,
                "score": stmt.excluded.score,
                "num_comments": stmt.excluded.num_comments,
                "title": stmt.excluded.title,
                "body": stmt.excluded.body,
                "extra_data": stmt.excluded.extra_data,
            },
        )
        
        await self.db.execute(stmt)
    
    async def _update_watermark(
        self,
        community_name: str,
        last_seen_post_id: str,
        last_seen_created_at: datetime,
        total_fetched: int,
        dedup_rate: float,
    ) -> None:
        """更新水位线"""
        await self.db.execute(
            pg_insert(CommunityCache)
            .values(
                community_name=community_name,
                last_seen_post_id=last_seen_post_id,
                last_seen_created_at=last_seen_created_at,
                total_posts_fetched=total_fetched,
                dedup_rate=dedup_rate,
                last_crawled_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "last_seen_post_id": last_seen_post_id,
                    "last_seen_created_at": last_seen_created_at,
                    "total_posts_fetched": CommunityCache.total_posts_fetched + total_fetched,
                    "dedup_rate": dedup_rate,
                    "last_crawled_at": datetime.now(timezone.utc),
                },
            )
        )
        await self.db.commit()


__all__ = ["IncrementalCrawler"]

