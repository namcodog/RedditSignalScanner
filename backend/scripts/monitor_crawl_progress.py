#!/usr/bin/env python3
"""
抓取进度监控脚本

功能：
1. 实时监控抓取进度
2. 显示每个社区的抓取状态
3. 计算预计完成时间
4. 检测异常情况

使用方法：
    python backend/scripts/monitor_crawl_progress.py
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text
from app.db.session import SessionFactory


async def monitor_progress():
    """监控抓取进度"""
    print("=" * 100)
    print(f"🔍 Reddit 抓取进度监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    async with SessionFactory() as session:
        # 1. 社区池状态
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE priority = 'high') as high,
                COUNT(*) FILTER (WHERE priority = 'medium') as medium,
                COUNT(*) FILTER (WHERE priority = 'low') as low
            FROM community_pool 
            WHERE is_active = true
        """))
        pool_stats = result.fetchone()
        
        print(f"\n📊 社区池状态:")
        print(f"  总数: {pool_stats[0]} 个社区")
        print(f"  HIGH: {pool_stats[1]} 个 | MEDIUM: {pool_stats[2]} 个 | LOW: {pool_stats[3]} 个")
        
        # 2. 抓取覆盖率
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT subreddit) 
            FROM posts_hot 
            WHERE subreddit IS NOT NULL
        """))
        covered_communities = result.scalar()
        coverage_rate = (covered_communities / pool_stats[0] * 100) if pool_stats[0] > 0 else 0
        
        print(f"\n📈 覆盖率:")
        print(f"  已抓取社区: {covered_communities} / {pool_stats[0]} ({coverage_rate:.1f}%)")
        print(f"  未抓取社区: {pool_stats[0] - covered_communities} 个")
        
        # 3. 数据量统计
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as hot_posts,
                (SELECT COUNT(*) FROM posts_raw) as raw_posts,
                (SELECT COUNT(*) FROM comments) as comments
            FROM posts_hot
        """))
        data_stats = result.fetchone()
        
        print(f"\n📦 数据存储:")
        print(f"  posts_hot (热缓存): {data_stats[0]:,} 条")
        print(f"  posts_raw (历史版本): {data_stats[1]:,} 条")
        print(f"  comments (评论): {data_stats[2]:,} 条")
        
        # 4. 目标进度
        target_posts = pool_stats[0] * 1000  # 165社区 × 1000帖子
        current_posts = data_stats[0]
        progress = (current_posts / target_posts * 100) if target_posts > 0 else 0
        remaining_posts = target_posts - current_posts
        
        print(f"\n🎯 目标进度:")
        print(f"  目标: {target_posts:,} 条帖子 ({pool_stats[0]} 社区 × 1,000 帖子)")
        print(f"  当前: {current_posts:,} 条帖子")
        print(f"  进度: {progress:.2f}%")
        print(f"  剩余: {remaining_posts:,} 条帖子")
        
        # 5. 今日增长
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as today_posts,
                COUNT(DISTINCT subreddit) as today_communities
            FROM posts_hot 
            WHERE cached_at >= CURRENT_DATE
        """))
        today_stats = result.fetchone()
        
        print(f"\n📅 今日增长:")
        print(f"  新增帖子: {today_stats[0]:,} 条")
        print(f"  涉及社区: {today_stats[1]} 个")
        
        # 6. 预计完成时间
        if today_stats[0] > 0:
            days_needed = remaining_posts / today_stats[0]
            completion_date = datetime.now() + timedelta(days=days_needed)
            print(f"\n⏱️  预计完成:")
            print(f"  按当前速度: {days_needed:.1f} 天")
            print(f"  预计日期: {completion_date.strftime('%Y-%m-%d')}")
        else:
            print(f"\n⚠️  警告: 今日无新增数据，请检查抓取任务是否正常运行！")
        
        # 7. 各社区详情（前20个）
        result = await session.execute(text("""
            SELECT 
                subreddit,
                COUNT(*) as total_posts,
                MAX(cached_at) as last_crawl,
                COUNT(*) FILTER (WHERE cached_at >= CURRENT_DATE) as today_posts
            FROM posts_hot
            WHERE subreddit IS NOT NULL
            GROUP BY subreddit
            ORDER BY total_posts DESC
            LIMIT 20
        """))
        
        print(f"\n📋 社区抓取详情 (前20个):")
        print(f"  {'社区名':<30} {'总帖子数':>10} {'今日新增':>10} {'最后抓取时间':<25}")
        print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*25}")
        for row in result.fetchall():
            last_crawl = row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else 'N/A'
            print(f"  {row[0]:<30} {row[1]:>10,} {row[3]:>10} {last_crawl:<25}")
        
        # 8. 未抓取的社区（前20个）
        result = await session.execute(text("""
            SELECT cp.name, cp.priority, cp.tier
            FROM community_pool cp
            LEFT JOIN posts_hot ph ON cp.name = ph.subreddit
            WHERE cp.is_active = true AND ph.subreddit IS NULL
            ORDER BY cp.priority DESC, cp.name
            LIMIT 20
        """))
        uncovered = result.fetchall()
        
        if uncovered:
            print(f"\n⚠️  未抓取的社区 (前20个):")
            for row in uncovered:
                print(f"  {row[0]:<30} priority={row[1]:<6} tier={row[2]}")
        
        # 9. 限速检查
        print(f"\n🔧 Reddit API 限速配置:")
        from app.core.config import get_settings
        settings = get_settings()
        print(f"  rate_limit: {settings.reddit_rate_limit} 次/分钟")
        print(f"  max_concurrency: {settings.reddit_max_concurrency} 个并发")
        print(f"  request_timeout: {settings.reddit_request_timeout_seconds} 秒")
        
        # 10. 建议
        print(f"\n💡 建议:")
        if coverage_rate < 50:
            print(f"  ⚠️  覆盖率较低({coverage_rate:.1f}%)，建议手动触发全量抓取")
            print(f"      命令: cd backend && PYTHONPATH=. python -c \"from app.core.celery_app import celery_app; celery_app.send_task('tasks.crawler.crawl_seed_communities')\"")
        
        if today_stats[0] == 0:
            print(f"  ⚠️  今日无新增数据，请检查:")
            print(f"      1. Celery Worker 是否运行: ps aux | grep celery")
            print(f"      2. Redis 是否运行: redis-cli ping")
            print(f"      3. 查看日志: tail -f backend/tmp/celery_worker*.log")
        
        if progress < 10 and days_needed > 20:
            print(f"  ⚠️  按当前速度需要{days_needed:.1f}天完成，超过目标17天")
            print(f"      建议增加抓取频率或并发数")
        
        print("\n" + "=" * 100)


if __name__ == "__main__":
    asyncio.run(monitor_progress())

