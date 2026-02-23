#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/Users/hujia/Desktop/RedditSignalScanner/backend')

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient


async def main():
    print("Step 1: 获取配置...")
    settings = get_settings()
    print(f"Step 2: 配置获取成功 (client_id={settings.reddit_client_id[:10]}...)")

    print("Step 3: 初始化Reddit客户端...")
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
    ) as reddit:
        print("Step 4: 客户端初始化成功")
        print("Step 5: 开始抓取...")
        posts = await reddit.fetch_subreddit_posts_paginated(
            subreddit="AmazonDSPDrivers",
            time_filter="month",
            sort="new",
            max_posts=10
        )
        print(f"Step 6: ✅ 获取到 {len(posts)} 个帖子")


if __name__ == "__main__":
    print("Starting...")
    asyncio.run(main())
    print("Done!")

