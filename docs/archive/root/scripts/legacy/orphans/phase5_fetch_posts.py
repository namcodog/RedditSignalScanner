#!/usr/bin/env python3
"""
Phase 5: 15个次高价值社区 - 12个月帖子抓取
使用 Celery 任务来抓取帖子
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionFactory
from app.core.celery_app import celery_app
from sqlalchemy import text
from app.utils.subreddit import normalize_subreddit_name


async def main():
    """主函数"""
    print('=' * 100)
    print('Phase 5: 15个次高价值社区 - 12个月帖子抓取')
    print('=' * 100)
    print()

    # 15个次高价值社区
    tier2_15 = [
        'AmazonDSPDrivers', 'AmazonFC', 'AmazonVine', 'AmazonWarehousingAndDelivery',
        'FBAOnlineRetail', 'Flipping', 'InstacartShoppers', 'ShopifyDropship',
        'WalmartEmployees', 'amazonreviews', 'ecommerce', 'shopify',
        'tiktokshopfinds', 'walmart', 'walmartworkers'
    ]

    print(f'📋 目标社区: {len(tier2_15)} 个')
    for i, sub in enumerate(tier2_15, 1):
        print(f'  {i}. r/{sub}')
    print()

    # 规范化社区名用于 posts_raw 查询（去前缀+小写）
    tier2_15_keys = [normalize_subreddit_name(s).lower() for s in tier2_15]

    # 检查当前状态（统一使用 lower(subreddit) 对齐存储格式）
    async with SessionFactory() as session:
        r = await session.execute(text('''
            SELECT
                subreddit,
                COUNT(*) as post_count,
                MIN(created_at) as earliest,
                MAX(created_at) as latest
            FROM posts_raw
            WHERE lower(subreddit) = ANY(:subs)
              AND is_current = true
            GROUP BY subreddit
            ORDER BY post_count DESC
        '''), {'subs': tier2_15_keys})

        rows = r.fetchall()
        if rows:
            print('📊 当前数据状态:')
            for row in rows:
                sub, count, earliest, latest = row
                print(f'  - {sub}: {count:,} 帖子 ({earliest.strftime("%Y-%m-%d")} ~ {latest.strftime("%Y-%m-%d")})')
            print()

    print()
    print('=' * 100)
    print('开始抓取（使用 Celery 任务）')
    print('=' * 100)
    print()

    # 抓取策略
    strategies = ['top', 'new', 'hot']
    time_filter = 'year'  # 最近12个月
    limit_per_strategy = 500  # 每个策略最多500个帖子

    task_ids = []

    for i, subreddit in enumerate(tier2_15, 1):
        print(f'[{i}/{len(tier2_15)}] 提交任务: r/{subreddit}')

        for strategy in strategies:
            # 使用 Celery 任务
            task = celery_app.send_task(
                'app.tasks.crawl_tasks.crawl_community_incremental',
                args=[subreddit],
                kwargs={
                    'strategy': strategy,
                    'time_filter': time_filter,
                    'limit': limit_per_strategy,
                    'fetch_comments': False,
                },
            )
            task_ids.append((subreddit, strategy, task.id))
            print(f'  - 任务已提交: {strategy} (task_id={task.id})')

        print()

    print('=' * 100)
    print('所有任务已提交')
    print('=' * 100)
    print()
    print(f'📊 总任务数: {len(task_ids)}')
    print()
    print('💡 提示:')
    print('  - 任务将在后台异步执行')
    print('  - 使用以下命令监控进度:')
    print()
    print('  python3 << EOF')
    print('import asyncio')
    print('import sys')
    print('sys.path.insert(0, "/Users/hujia/Desktop/RedditSignalScanner")')
    print('from backend.app.db.session import SessionFactory')
    print('from sqlalchemy import text')
    print()
    print('async def main():')
    print('    tier2_15 = ["AmazonDSPDrivers", "AmazonFC", "AmazonVine", "AmazonWarehousingAndDelivery",')
    print('                "FBAOnlineRetail", "Flipping", "InstacartShoppers", "ShopifyDropship",')
    print('                "WalmartEmployees", "amazonreviews", "ecommerce", "shopify",')
    print('                "tiktokshopfinds", "walmart", "walmartworkers"]')
    print('    async with SessionFactory() as session:')
    print('        r = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE subreddit = ANY(:subs) AND is_current = true"), {"subs": tier2_15})')
    print('        posts = r.first()[0]')
    print('        print(f"Phase 5 帖子数: {posts:,}")')
    print()
    print('asyncio.run(main())')
    print('EOF')
    print()



if __name__ == '__main__':
    asyncio.run(main())
