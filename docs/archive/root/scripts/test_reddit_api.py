#!/usr/bin/env python3
"""测试Reddit API的不同抓取方法"""

import asyncio
import sys
sys.path.insert(0, '/Users/hujia/Desktop/RedditSignalScanner/backend')

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient


async def test_methods():
    settings = get_settings()
    
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
    ) as reddit:
        
        subreddit = "AmazonDSPDrivers"
        
        print(f"\n{'='*60}")
        print(f"测试社区: r/{subreddit}")
        print(f"{'='*60}\n")
        
        # 方法1：使用/new端点（最近30天）
        print("方法1：使用/new端点（time_filter=month）")
        try:
            import traceback
            posts = await reddit.fetch_subreddit_posts_paginated(
                subreddit=subreddit,
                time_filter="month",
                sort="new",
                max_posts=100
            )
            print(f"   ✅ 获取到 {len(posts)} 个帖子")
            if posts:
                print(f"   📅 最新帖子时间: {posts[0].created_utc}")
                print(f"   📅 最旧帖子时间: {posts[-1].created_utc}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            traceback.print_exc()
        
        # 方法2：使用timestamp搜索（2024-11）
        print("\n方法2：使用timestamp搜索（2024-11-01 ~ 2024-11-30）")
        try:
            import datetime
            start = int(datetime.datetime(2024, 11, 1, tzinfo=datetime.timezone.utc).timestamp())
            end = int(datetime.datetime(2024, 11, 30, tzinfo=datetime.timezone.utc).timestamp())
            
            posts = await reddit.fetch_subreddit_posts_by_timestamp(
                subreddit=subreddit,
                start_epoch=start,
                end_epoch=end,
                sort="new",
                max_posts=100
            )
            print(f"   ✅ 获取到 {len(posts)} 个帖子")
            if posts:
                print(f"   📅 最新帖子时间: {posts[0].created_utc}")
                print(f"   📅 最旧帖子时间: {posts[-1].created_utc}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 方法3：使用timestamp搜索（最近7天）
        print("\n方法3：使用timestamp搜索（最近7天）")
        try:
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            start = int((now - datetime.timedelta(days=7)).timestamp())
            end = int(now.timestamp())
            
            posts = await reddit.fetch_subreddit_posts_by_timestamp(
                subreddit=subreddit,
                start_epoch=start,
                end_epoch=end,
                sort="new",
                max_posts=100
            )
            print(f"   ✅ 获取到 {len(posts)} 个帖子")
            if posts:
                print(f"   📅 最新帖子时间: {posts[0].created_utc}")
                print(f"   📅 最旧帖子时间: {posts[-1].created_utc}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 方法4：使用/new端点（all time）
        print("\n方法4：使用/new端点（time_filter=all）")
        try:
            posts = await reddit.fetch_subreddit_posts_paginated(
                subreddit=subreddit,
                time_filter="all",
                sort="new",
                max_posts=100
            )
            print(f"   ✅ 获取到 {len(posts)} 个帖子")
            if posts:
                print(f"   📅 最新帖子时间: {posts[0].created_utc}")
                print(f"   📅 最旧帖子时间: {posts[-1].created_utc}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        print(f"\n{'='*60}")
        print("测试完成")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_methods())

