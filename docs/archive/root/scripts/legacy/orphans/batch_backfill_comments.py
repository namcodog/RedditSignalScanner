#!/usr/bin/env python3
"""批量回填评论脚本 - 用于 Day 1 首次补充抓取"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.comments_ingest import persist_comments
from app.services.labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.services.reddit_client import RedditAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def get_target_posts(
    session: AsyncSession,
    *,
    posts_per_subreddit: int = 20,
    min_comments: int = 3,
    skip_existing: bool = True,
) -> list[dict[str, Any]]:
    """获取需要抓取评论的帖子列表（每个社区最近 N 个帖子）

    Args:
        session: 数据库会话
        posts_per_subreddit: 每个社区抓取的帖子数
        min_comments: 最小评论数阈值
        skip_existing: 是否跳过已抓取评论的帖子（断点续抓）
    """
    # 构建排除条件
    exclude_clause = ""
    if skip_existing:
        exclude_clause = """
              AND source_post_id NOT IN (
                  SELECT DISTINCT source_post_id FROM comments
              )
        """

    query = text(
        f"""
        WITH ranked_posts AS (
            SELECT
                source_post_id,
                subreddit,
                num_comments,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY subreddit
                    ORDER BY created_at DESC
                ) as rn
            FROM posts_raw
            WHERE is_current = TRUE
              AND num_comments >= :min_comments
              {exclude_clause}
        )
        SELECT
            source_post_id,
            subreddit,
            num_comments
        FROM ranked_posts
        WHERE rn <= :limit
        ORDER BY subreddit, created_at DESC
        """
    )
    result = await session.execute(
        query, {"limit": posts_per_subreddit, "min_comments": min_comments}
    )
    rows = result.fetchall()
    return [
        {
            "source_post_id": row[0],
            "subreddit": row[1],
            "num_comments": row[2],
        }
        for row in rows
    ]


async def backfill_batch(
    reddit: RedditAPIClient,
    session: AsyncSession,
    posts: list[dict[str, Any]],
    *,
    limit_per_post: int = 20,
    batch_size: int = 10,
) -> dict[str, int]:
    """批量回填评论（带进度监控和错误重试）"""
    total_processed = 0
    total_labeled = 0
    total_failed = 0
    total_skipped = 0

    start_time = datetime.now(timezone.utc)
    last_report_time = start_time

    for i, post in enumerate(posts, 1):
        pid = post["source_post_id"]
        subreddit = post["subreddit"]

        # 每 50 个帖子报告一次进度
        if i % 50 == 0:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            rate = i / elapsed if elapsed > 0 else 0
            eta_seconds = (len(posts) - i) / rate if rate > 0 else 0
            logger.info(
                "📊 进度: %d/%d (%.1f%%) | 速率: %.2f 帖子/秒 | 预计剩余: %.1f 分钟",
                i,
                len(posts),
                (i / len(posts)) * 100,
                rate,
                eta_seconds / 60,
            )
            logger.info(
                "   已处理: %d 评论 | 已标注: %d | 失败: %d | 跳过: %d",
                total_processed,
                total_labeled,
                total_failed,
                total_skipped,
            )

        try:
            logger.debug(
                "📥 [%d/%d] 抓取帖子 %s (%s) 的评论...",
                i,
                len(posts),
                pid,
                subreddit,
            )

            # 抓取评论（RedditAPIClient 内部已有速率限制和重试机制）
            items = await reddit.fetch_post_comments(
                pid, sort="confidence", depth=8, limit=limit_per_post, mode="full"
            )

            if not items:
                logger.debug("  ⚠️  无评论，跳过")
                total_skipped += 1
                continue

            # 持久化评论
            n = await persist_comments(
                session,
                source_post_id=pid,
                subreddit=subreddit,
                comments=items,
            )
            total_processed += n

            # 标注评论
            ids = [c.get("id") for c in items if c.get("id")]
            if ids:
                n1 = await classify_and_label_comments(session, ids)
                n2 = await extract_and_label_entities_for_comments(session, ids)
                total_labeled += n1 + n2

            # 每个帖子独立提交，避免事务失败传播
            await session.commit()

            logger.debug(
                "  ✅ 处理 %d 条评论，标注 %d 条",
                n,
                n1 + n2 if ids else 0,
            )

            # 每 batch_size 个帖子报告一次
            if i % batch_size == 0:
                logger.info("💾 已提交事务（%d/%d）", i, len(posts))

        except Exception as e:
            logger.warning(
                "  ❌ 失败: %s (%s): %s",
                pid,
                subreddit,
                str(e)[:100],
                exc_info=False,
            )
            total_failed += 1
            # 回滚失败的事务
            await session.rollback()
            # 不要因为单个失败而中断整个批次
            continue

    return {
        "processed": total_processed,
        "labeled": total_labeled,
        "failed": total_failed,
        "skipped": total_skipped,
    }


async def main() -> None:
    """主函数"""
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 80)
    logger.info("🚀 开始批量回填评论（断点续抓模式）")
    logger.info("=" * 80)
    
    settings = get_settings()
    
    async with SessionFactory() as session:
        # 获取目标帖子（跳过已抓取的）
        logger.info("📋 获取目标帖子列表（跳过已抓取评论的帖子）...")
        posts = await get_target_posts(
            session,
            posts_per_subreddit=60,  # 20 → 60（提升数据深度）
            min_comments=3,
            skip_existing=True,  # 启用断点续抓
        )
        logger.info("✅ 找到 %d 个帖子需要抓取评论（已排除已抓取的帖子）", len(posts))
        
        # 按社区分组统计
        subreddits = {}
        for p in posts:
            sub = p["subreddit"]
            subreddits[sub] = subreddits.get(sub, 0) + 1
        logger.info("📊 涉及 %d 个社区", len(subreddits))
    
    # 批量抓取
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    ) as reddit:
        async with SessionFactory() as session:
            result = await backfill_batch(
                reddit,
                session,
                posts,
                limit_per_post=500,  # 全量评论：500（Reddit API 单次最大值）
            )
    
    # 统计结果
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("=" * 80)
    logger.info("🎉 批量回填完成！")
    logger.info("=" * 80)
    logger.info("📊 统计结果:")
    logger.info("  - 目标帖子数: %d", len(posts))
    logger.info("  - 处理评论数: %d", result["processed"])
    logger.info("  - 标注评论数: %d", result["labeled"])
    logger.info("  - 失败帖子数: %d", result["failed"])
    logger.info("  - 跳过帖子数: %d (无评论)", result["skipped"])
    logger.info("  - 成功率: %.2f%%", ((len(posts) - result["failed"]) / len(posts)) * 100 if len(posts) > 0 else 0)
    logger.info("  - 平均评论数/帖子: %.2f", result["processed"] / (len(posts) - result["skipped"]) if (len(posts) - result["skipped"]) > 0 else 0)
    logger.info("  - 总耗时: %.2f 秒 (%.2f 分钟)", duration, duration / 60)
    logger.info("  - 平均速率: %.2f 帖子/秒", len(posts) / duration if duration > 0 else 0)
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

