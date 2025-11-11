#!/usr/bin/env python3
"""
测试 PRAW 客户端的 limit 能力

目的：验证 backend/app/clients/reddit_client.py 的 RedditClient 能否：
1. 支持 limit > 100
2. 支持 limit=None 深度翻页
3. 实际能抓取多少帖子
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.reddit_client import RedditClient
from app.core.config import get_settings


async def test_praw_limits():
    settings = get_settings()
    
    client = RedditClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )
    
    test_subreddit = "ecommerce"
    
    print("=" * 60)
    print("测试 PRAW RedditClient 的 limit 能力")
    print("=" * 60)
    
    # 测试 1: limit=100（默认）
    print("\n📊 测试 1: limit=100")
    try:
        posts_100 = await client.fetch_subreddit_posts(
            test_subreddit,
            limit=100,
            time_filter="all",
        )
        print(f"✅ limit=100: 实际抓取 {len(posts_100)} 帖")
    except Exception as e:
        print(f"❌ limit=100 失败: {e}")
    
    # 测试 2: limit=500（超过 100）
    print("\n📊 测试 2: limit=500")
    try:
        posts_500 = await client.fetch_subreddit_posts(
            test_subreddit,
            limit=500,
            time_filter="all",
        )
        print(f"✅ limit=500: 实际抓取 {len(posts_500)} 帖")
    except Exception as e:
        print(f"❌ limit=500 失败: {e}")
    
    # 测试 3: limit=1000
    print("\n📊 测试 3: limit=1000")
    try:
        posts_1000 = await client.fetch_subreddit_posts(
            test_subreddit,
            limit=1000,
            time_filter="all",
        )
        print(f"✅ limit=1000: 实际抓取 {len(posts_1000)} 帖")
    except Exception as e:
        print(f"❌ limit=1000 失败: {e}")
    
    print("\n" + "=" * 60)
    print("结论:")
    print("=" * 60)
    print("如果 limit=500 和 limit=1000 都能抓取超过 100 帖，")
    print("说明 PRAW 支持深度翻页，可以用于语义库构建。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_praw_limits())

