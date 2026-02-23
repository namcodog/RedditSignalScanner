#!/usr/bin/env python3
"""测试高价值社区评论抓取功能

用法：
    python backend/scripts/test_high_value_comments.py
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient
from app.db.session import SessionFactory
from app.services.comments_ingest import persist_comments


async def test_single_community_comments(subreddit: str = "FacebookAds", post_limit: int = 5):
    """测试单个高价值社区的评论抓取

    Args:
        subreddit: 社区名称（不含 r/ 前缀）
        post_limit: 抓取帖子数量
    """
    settings = get_settings()

    print(f"\n🎯 测试高价值社区评论抓取：r/{subreddit}")
    print(f"   配置：每社区 {post_limit} 个帖子，全量评论（depth=8, limit=500）\n")

    total_posts = 0
    total_comments = 0

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
            try:
                # 1. 抓取帖子
                print(f"📥 正在抓取 r/{subreddit} 的帖子...")
                posts, _ = await reddit.fetch_subreddit_posts(
                    subreddit, limit=post_limit, time_filter="week", sort="top"
                )
                total_posts = len(posts)
                print(f"✅ 获取到 {total_posts} 个帖子\n")
                
                # 2. 抓取每个帖子的全量评论
                for idx, p in enumerate(posts, 1):
                    try:
                        print(f"[{idx}/{total_posts}] 帖子 {p.id} ({p.title[:50]}...)")
                        
                        # 🔥 全量评论抓取：depth=8, limit=500, mode="full"
                        items = await reddit.fetch_post_comments(
                            p.id, sort="confidence", depth=8, limit=500, mode="full"
                        )
                        
                        if not items:
                            print(f"  ⚠️  无评论")
                            continue
                        
                        # 3. 持久化评论
                        await persist_comments(
                            session, source_post_id=p.id, subreddit=subreddit, comments=items
                        )
                        
                        total_comments += len(items)
                        print(f"  ✅ {len(items)} 条评论已保存")
                        
                    except Exception as e:
                        print(f"  ❌ 失败: {e}")
                        continue
                
                await session.commit()
                
            except Exception as e:
                print(f"❌ 社区 r/{subreddit} 抓取失败: {e}")
                return
    
    print(f"\n🎉 测试完成！")
    print(f"   社区：r/{subreddit}")
    print(f"   帖子数：{total_posts}")
    print(f"   评论数：{total_comments}")
    print(f"   平均评论/帖：{total_comments / total_posts if total_posts > 0 else 0:.1f}")


async def verify_comments_in_db(subreddit: str = "FacebookAds"):
    """验证评论是否正确写入数据库
    
    Args:
        subreddit: 社区名称（不含 r/ 前缀）
    """
    from sqlalchemy import select, func
    from app.models.comment import Comment
    
    print(f"\n🔍 验证数据库中的评论数据：r/{subreddit}")
    
    async with SessionFactory() as session:
        # 统计评论数量
        stmt = select(func.count(Comment.id)).where(Comment.subreddit == subreddit)
        result = await session.execute(stmt)
        total_count = result.scalar_one()
        
        print(f"   总评论数：{total_count}")
        
        # 统计不同深度的评论
        stmt = select(Comment.depth, func.count(Comment.id)).where(
            Comment.subreddit == subreddit
        ).group_by(Comment.depth).order_by(Comment.depth)
        result = await session.execute(stmt)
        depth_stats = result.all()
        
        print(f"   深度分布：")
        for depth, count in depth_stats:
            print(f"     深度 {depth}: {count} 条")
        
        # 查询最新的5条评论
        stmt = select(Comment).where(
            Comment.subreddit == subreddit
        ).order_by(Comment.created_utc.desc()).limit(5)
        result = await session.execute(stmt)
        recent_comments = result.scalars().all()

        print(f"\n   最新5条评论：")
        for c in recent_comments:
            body_preview = c.body[:50] if c.body else ""
            print(f"     - {c.reddit_comment_id} (深度{c.depth}): {body_preview}...")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试高价值社区评论抓取")
    parser.add_argument("--subreddit", default="FacebookAds", help="社区名称（不含 r/ 前缀）")
    parser.add_argument("--posts", type=int, default=5, help="抓取帖子数量")
    parser.add_argument("--verify-only", action="store_true", help="仅验证数据库，不抓取")
    
    args = parser.parse_args()
    
    if args.verify_only:
        asyncio.run(verify_comments_in_db(args.subreddit))
    else:
        asyncio.run(test_single_community_comments(args.subreddit, args.posts))
        asyncio.run(verify_comments_in_db(args.subreddit))

