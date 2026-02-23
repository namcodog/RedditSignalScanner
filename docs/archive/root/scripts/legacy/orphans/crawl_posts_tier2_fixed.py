#!/usr/bin/env python3
"""
次高价值社区帖子抓取脚本（修复版）

使用正确的 Reddit API 方法（/r/{subreddit}/new）而不是 timestamp 搜索
"""
from __future__ import annotations

import asyncio
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient
from app.utils.subreddit import normalize_subreddit_name
from app.services.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore
from sqlalchemy import text


async def main():
    """主函数"""
    print('=' * 80)
    print('次高价值社区帖子抓取任务（修复版）')
    print('=' * 80)
    print()
    print('📋 任务说明：')
    print('  - 目标：15个次高价值社区')
    print('  - 策略：使用 /r/{subreddit}/new 端点（time_filter=all）')
    print('  - 方法：自动分页（最多1000个帖子/社区）')
    print('  - 评论：不抓取（仅抓取帖子）')
    print()
    
    # 读取次高价值社区列表
    csv_file = Path(__file__).parent.parent.parent / '次高价值社区池_15社区.csv'
    
    if not csv_file.exists():
        print(f'❌ 错误：找不到CSV文件：{csv_file}')
        return
    
    communities = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subreddit = row.get('社区名称', '').strip()
            # 跳过说明行和空行
            if subreddit and not subreddit.startswith('说明') and not subreddit.startswith('抓取策略') and subreddit.startswith('r/'):
                communities.append(subreddit)
    
    print(f'✅ 读取到 {len(communities)} 个次高价值社区')
    print()
    
    # 显示所有社区
    print('📊 社区列表：')
    for i, community in enumerate(communities, 1):
        print(f'  {i}. {community}')
    print()
    
    # 规范化社区名（去前缀+小写）用于 posts_raw 查询
    from app.utils.subreddit import normalize_subreddit_name
    communities_keys = [normalize_subreddit_name(c).lower() for c in communities]

    # 确认当前数据库状态（使用 lower(subreddit) 对齐存储格式）
    async with SessionFactory() as db:
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) FILTER (WHERE is_current = true) as current_posts
            FROM posts_raw
            WHERE lower(subreddit) = ANY(:communities)
        '''), {'communities': communities_keys})
        row = result.fetchone()
        
        print(f'📊 当前数据库状态：')
        print(f'  - 已有数据的社区数：{row[0]} / {len(communities)}')
        print(f'  - 当前版本帖子数：{row[1]:,} 条')
        print()
    
    # 确认是否继续
    print('⚠️ 注意：')
    print('  - 这个脚本将使用正确的 Reddit API 方法重新抓取帖子')
    print('  - 每个社区最多抓取 1000 个帖子（Reddit API 限制）')
    print('  - 预计耗时：15-30 分钟（取决于社区大小）')
    print()
    
    # 开始抓取
    settings = get_settings()
    start_time = datetime.now()
    success_count = 0
    failed_count = 0
    failed_communities = []
    
    # 初始化全局限流器
    limiter = None
    try:
        rclient = redis.Redis.from_url(settings.reddit_cache_redis_url)
        limiter = GlobalRateLimiter(
            rclient,
            limit=max(1, int(settings.reddit_rate_limit)),
            window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
            client_id=settings.reddit_client_id or "default",
        )
        print('✅ 全局限流器初始化成功')
    except Exception as e:
        print(f'⚠️ 全局限流器初始化失败：{e}')
        print('   将使用本地限流器')
    
    print()
    print('=' * 80)
    print('开始抓取')
    print('=' * 80)
    print()
    
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
        global_rate_limiter=limiter,
    ) as reddit:
        async with SessionFactory() as session:
            crawler = IncrementalCrawler(session, reddit, hot_cache_ttl_hours=24)
            
            for idx, community in enumerate(communities, 1):
                print(f'[{idx}/{len(communities)}] 抓取社区：{community}')
                try:
                    sub = community[2:] if community.lower().startswith('r/') else community
                    
                    # 使用正确的方法：fetch_subreddit_posts_paginated
                    # sort="new" 确保获取最新的帖子
                    # time_filter="all" 确保获取所有时间范围的帖子
                    posts = await reddit.fetch_subreddit_posts_paginated(
                        subreddit=sub,
                        max_posts=1000,  # Reddit API 限制
                        time_filter="all",
                        sort="new"
                    )
                    
                    print(f'  ✅ 抓取到 {len(posts)} 个帖子')
                    
                    if posts:
                        # 入库
                        res = await crawler.ingest_posts_batch(community, posts)
                        print(f'  ✅ 入库完成：new={res["new"]}, updated={res["updated"]}, dup={res["duplicates"]}')
                    else:
                        print(f'  ⚠️ 该社区没有帖子')
                    
                    success_count += 1
                    print(f'  ✅ 社区 {community} 抓取完成')
                except Exception as e:
                    failed_count += 1
                    failed_communities.append(community)
                    print(f'  ❌ 社区 {community} 抓取失败：{e}')
                print()
                
                # 每10个社区显示一次进度
                if idx % 5 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / idx
                    remaining = (len(communities) - idx) * avg_time
                    print('-' * 80)
                    print(f'📊 进度报告：')
                    print(f'  - 已完成：{idx}/{len(communities)} ({idx/len(communities)*100:.1f}%)')
                    print(f'  - 成功：{success_count} 个')
                    print(f'  - 失败：{failed_count} 个')
                    print(f'  - 已耗时：{elapsed/60:.1f} 分钟')
                    print(f'  - 预计剩余：{remaining/60:.1f} 分钟')
                    print('-' * 80)
                    print()
    
    # 最终统计
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print('=' * 80)
    print('抓取完成')
    print('=' * 80)
    print()
    
    # 查询最终数据（同样用 lower(subreddit) 与规范化 keys）
    async with SessionFactory() as db:
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) FILTER (WHERE is_current = true) as current_posts,
                COUNT(*) as total_posts
            FROM posts_raw
            WHERE lower(subreddit) = ANY(:communities)
        '''), {'communities': communities_keys})
        row = result.fetchone()
        
        print(f'📊 最终统计：')
        print(f'  - 社区数：{row[0]} / {len(communities)}')
        print(f'  - 当前版本帖子：{row[1]:,} 条')
        print(f'  - 总帖子数（含历史版本）：{row[2]:,} 条')
        print()
    
    print(f'📊 执行统计：')
    print(f'  - 成功：{success_count} 个社区')
    print(f'  - 失败：{failed_count} 个社区')
    print(f'  - 总耗时：{total_time/60:.1f} 分钟')
    print()
    
    if failed_communities:
        print('❌ 失败的社区：')
        for community in failed_communities:
            print(f'  - {community}')
        print()
    
    print('=' * 80)
    print('✅ 任务完成')
    print('=' * 80)


if __name__ == '__main__':
    asyncio.run(main())
