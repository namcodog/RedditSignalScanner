#!/usr/bin/env python3
"""
测试 Reddit 搜索 API 是否能返回数据
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.reddit_client import RedditAPIClient
from app.core.config import get_settings


async def test_search():
    settings = get_settings()
    client = RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )
    
    print("=" * 80)
    print("测试 Reddit 搜索 API")
    print("=" * 80)
    
    subreddit = "ecommerce"
    
    # 测试 1: 不带时间戳的简单搜索
    print("\n【测试 1】简单搜索（无时间限制）")
    print(f"查询: '*' (所有帖子)")
    try:
        posts, after = await client.search_subreddit_page(
            subreddit=subreddit,
            query="*",
            limit=10,
            sort="new",
            time_filter="month",
        )
        print(f"✅ 返回 {len(posts)} 条帖子")
        if posts:
            print(f"   第一条: {posts[0].title[:50]}...")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试 2: 带关键词的搜索
    print("\n【测试 2】关键词搜索")
    print(f"查询: 'amazon'")
    try:
        posts, after = await client.search_subreddit_page(
            subreddit=subreddit,
            query="amazon",
            limit=10,
            sort="new",
            time_filter="year",
        )
        print(f"✅ 返回 {len(posts)} 条帖子")
        if posts:
            print(f"   第一条: {posts[0].title[:50]}...")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试 3: 带时间戳的搜索（cloudsearch）
    print("\n【测试 3】时间戳范围搜索（cloudsearch）")
    # 2024-11-01 到 2024-11-08
    start_ts = 1730419200  # 2024-11-01 00:00:00 UTC
    end_ts = 1731024000    # 2024-11-08 00:00:00 UTC
    query = f"timestamp:{start_ts}..{end_ts}"
    print(f"查询: {query}")
    try:
        posts, after = await client.search_subreddit_page(
            subreddit=subreddit,
            query=query,
            limit=10,
            sort="new",
            syntax="cloudsearch",
        )
        print(f"✅ 返回 {len(posts)} 条帖子")
        if posts:
            print(f"   第一条: {posts[0].title[:50]}...")
        else:
            print("   ⚠️ 返回 0 条 - 时间戳查询可能不支持")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试 4: 使用 /new 列表（不是搜索）
    print("\n【测试 4】使用 /new 列表（对比）")
    try:
        posts, after = await client.fetch_posts_page(
            subreddit=subreddit,
            sort="new",
            limit=10,
        )
        print(f"✅ 返回 {len(posts)} 条帖子")
        if posts:
            print(f"   第一条: {posts[0].title[:50]}...")
            print(f"   创建时间: {posts[0].created_utc}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_search())

