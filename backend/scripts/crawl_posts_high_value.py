#!/usr/bin/env python3
"""
高价值社区帖子抓取脚本
抓取48个高价值社区（1000+帖子）的全量帖子数据
不抓取评论，只抓取帖子
"""
import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.celery_app import celery_app
from sqlalchemy import text
from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.incremental_crawler import IncrementalCrawler
from app.core.config import get_settings
from app.services.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore
from datetime import timezone, timedelta


def _build_month_slices(since_ym: str, until_ym: str) -> list[tuple[int, int]]:
    """Return list of (start_epoch, end_epoch) for each month in [since, until]."""
    from datetime import datetime
    def to_dt(ym: str) -> datetime:
        return datetime.strptime(ym + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    slices: list[tuple[int, int]] = []
    cur = to_dt(since_ym)
    end = to_dt(until_ym)
    # move end to first day next month for inclusive bound
    if end.month == 12:
        end_next = end.replace(year=end.year + 1, month=1)
    else:
        end_next = end.replace(month=end.month + 1)
    while cur < end_next:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        slices.append((int(cur.timestamp()), int((nxt - timedelta(seconds=1)).timestamp())))
        cur = nxt
    return slices


async def main():
    """主函数"""
    print('=' * 80)
    print('高价值社区帖子抓取任务')
    print('=' * 80)
    print()
    print('📋 任务说明：')
    print('  - 目标：48个高价值社区（1000+帖子）')
    print('  - 策略：全量抓取（time_filter=all）')
    print('  - 方法：多策略（top + new + hot）')
    print('  - 评论：不抓取（仅抓取帖子）')
    print()
    
    # 读取高价值社区列表
    csv_file = Path(__file__).parent.parent.parent / '高价值社区池_基于165社区.csv'
    
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
    
    print(f'✅ 读取到 {len(communities)} 个高价值社区')
    print()
    
    # 显示前10个社区
    print('📊 社区列表（前10个）：')
    for i, community in enumerate(communities[:10], 1):
        print(f'  {i}. {community}')
    if len(communities) > 10:
        print(f'  ... 还有 {len(communities) - 10} 个社区')
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
        print(f'  - 已有社区数：{row[0]} / {len(communities)}')
        print(f'  - 已有帖子数：{row[1]:,} 条')
        print()
    
    # 参数模式
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["comprehensive", "sliced"], default="comprehensive")
    parser.add_argument("--since", type=str, default="2018-01", help="YYYY-MM (sliced mode)")
    parser.add_argument("--until", type=str, default=datetime.now().strftime("%Y-%m"), help="YYYY-MM (sliced mode)")
    parser.add_argument("--per-slice", type=int, default=1000, help="Max posts per month slice")
    args = parser.parse_args()

    # 确认是否继续
    print('⚠️  注意：')
    print('  - 全量抓取会调用大量Reddit API')
    if args.mode == "comprehensive":
        print('  - 模式：综合三策略(top/new/hot)，每子上限≈3000')
    else:
        print('  - 模式：时间切片(月) + 搜索API，突破1000限制（每月上限可调）')
    print()
    
    confirm = input('是否继续？(yes/no): ').strip().lower()
    if confirm not in ['yes', 'y']:
        print('❌ 已取消')
        return
    
    print()
    print('=' * 80)
    print('开始抓取')
    print('=' * 80)
    print()
    
    # 抓取策略配置
    strategies = ['top', 'new', 'hot']
    time_filter = 'all'  # 全量抓取
    
    # 统计信息
    total_communities = len(communities)
    success_count = 0
    failed_count = 0
    failed_communities = []
    
    start_time = datetime.now()
    
    settings = get_settings()
    # 逐个社区抓取
    for idx, community in enumerate(communities, 1):
        print(f'[{idx}/{total_communities}] 抓取社区：{community} (mode={args.mode})')
        try:
            if args.mode == "comprehensive":
                # 旧模式：仍走 Celery 任务，调用 IncrementalCrawler 内置三策略
                for strategy in strategies:
                    print(f'  策略：{strategy} (time_filter={time_filter})')
                    result = celery_app.send_task(
                        'tasks.crawler.crawl_community',
                        args=[community],
                        kwargs={'sort': strategy, 'time_filter': time_filter, 'enable_comments': False}
                    )
                    task_result = result.get(timeout=300)
                    if task_result and task_result.get('status') == 'success':
                        cached = task_result.get('cached_count', 0)
                        print(f'    ✅ 成功：缓存 {cached} 个帖子')
                    else:
                        error = task_result.get('error', 'Unknown error') if task_result else 'No result'
                        print(f'    ⚠️ 失败：{error}')
            else:
                # 新模式：时间切片（月），走 RedditAPIClient + IncrementalCrawler.ingest_posts_batch 直接入库
                since = args.since
                until = args.until
                slices = _build_month_slices(since, until)
                # 构建客户端与写入器
                # Connect a global limiter so multiple shards coordinate capacity
                limiter = None
                try:
                    rclient = redis.Redis.from_url(settings.reddit_cache_redis_url)
                    limiter = GlobalRateLimiter(
                        rclient,
                        limit=max(1, int(settings.reddit_rate_limit)),
                        window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
                        client_id=settings.reddit_client_id or "default",
                    )
                except Exception as e:
                    print(f"WARN Global rate limiter init failed (sliced posts), fallback to local limiter: {e}")
                    limiter = None

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
                        sub = community[2:] if community.lower().startswith('r/') else community
                        posts = await reddit.fetch_posts_by_time_slices(subreddit=sub, slices=slices, per_slice_max=args.per_slice, sort='new')
                        res = await crawler.ingest_posts_batch(community, posts)
                        print(f"    ✅ 切片模式成功：new={res['new']}, updated={res['updated']}, dup={res['duplicates']} (total={len(posts)})")
            success_count += 1
            print(f'  ✅ 社区 {community} 抓取完成')
        except Exception as e:
            failed_count += 1
            failed_communities.append(community)
            print(f'  ❌ 社区 {community} 抓取失败：{e}')
        print()
        if idx % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / idx
            remaining = (total_communities - idx) * avg_time
            print('-' * 80)
            print(f'📊 进度报告：')
            print(f'  - 已完成：{idx}/{total_communities} ({idx/total_communities*100:.1f}%)')
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
    
    # 查询最终数据（同样使用 lower(subreddit) 与规范化 keys）
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
    
    print(f'⏱️  耗时：{total_time/60:.1f} 分钟')
    print(f'✅ 成功：{success_count} 个社区')
    print(f'❌ 失败：{failed_count} 个社区')
    
    if failed_communities:
        print()
        print(f'失败的社区列表：')
        for community in failed_communities:
            print(f'  - {community}')
    
    print()
    print('=' * 80)
    print('✅ 任务完成！')
    print('=' * 80)
    print()
    print('下一步：')
    print('  1. 查看数据统计：make pool-stats')
    print('  2. 查看帖子增长：make posts-growth-7d')
    print('  3. 执行次高价值社区抓取：python scripts/crawl_posts_medium_value.py')


if __name__ == '__main__':
    asyncio.run(main())
