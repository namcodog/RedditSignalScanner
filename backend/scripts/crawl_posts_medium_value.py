#!/usr/bin/env python3
"""
次高价值社区帖子抓取脚本
抓取15个次高价值社区（500-999帖子）的最近12个月帖子数据
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


async def main():
    """主函数"""
    print('=' * 80)
    print('次高价值社区帖子抓取任务')
    print('=' * 80)
    print()
    print('📋 任务说明：')
    print('  - 目标：15个次高价值社区（500-999帖子）')
    print('  - 策略：最近12个月（time_filter=year）')
    print('  - 方法：多策略（top + new + hot）')
    print('  - 评论：不抓取（仅抓取帖子）')
    print()
    
    # 读取次高价值社区列表
    csv_file = Path(__file__).parent.parent.parent / '次高价值社区池_基于165社区.csv'
    
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
    
    # 确认当前数据库状态
    async with SessionFactory() as db:
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) FILTER (WHERE is_current = true) as current_posts
            FROM posts_raw
            WHERE subreddit = ANY(:communities)
        '''), {'communities': communities})
        row = result.fetchone()
        
        print(f'📊 当前数据库状态：')
        print(f'  - 已有社区数：{row[0]} / {len(communities)}')
        print(f'  - 已有帖子数：{row[1]:,} 条')
        print()
    
    # 确认是否继续
    print('⚠️  注意：')
    print('  - 抓取最近12个月的帖子')
    print('  - 预计耗时：30分钟')
    print('  - 预计新增帖子：约8,000个')
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
    time_filter = 'year'  # 最近12个月
    
    # 统计信息
    total_communities = len(communities)
    success_count = 0
    failed_count = 0
    failed_communities = []
    
    start_time = datetime.now()
    
    # 逐个社区抓取
    for idx, community in enumerate(communities, 1):
        print(f'[{idx}/{total_communities}] 抓取社区：{community}')
        
        try:
            # 对每个策略都抓取一次
            for strategy in strategies:
                print(f'  策略：{strategy} (time_filter={time_filter})')

                # 调用Celery任务（同步执行）
                result = celery_app.send_task(
                    'tasks.crawler.crawl_community',
                    args=[community],
                    kwargs={
                        'sort': strategy,
                        'time_filter': time_filter,
                        'enable_comments': False  # 不抓取评论
                    }
                )

                # 等待任务完成
                task_result = result.get(timeout=300)  # 5分钟超时

                if task_result and task_result.get('status') == 'success':
                    cached = task_result.get('cached_count', 0)
                    print(f'    ✅ 成功：缓存 {cached} 个帖子')
                else:
                    error = task_result.get('error', 'Unknown error') if task_result else 'No result'
                    print(f'    ⚠️ 失败：{error}')
            
            success_count += 1
            print(f'  ✅ 社区 {community} 抓取完成')
            
        except Exception as e:
            failed_count += 1
            failed_communities.append(community)
            print(f'  ❌ 社区 {community} 抓取失败：{e}')
        
        print()
    
    # 最终统计
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print('=' * 80)
    print('抓取完成')
    print('=' * 80)
    print()
    
    # 查询最终数据
    async with SessionFactory() as db:
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) FILTER (WHERE is_current = true) as current_posts,
                COUNT(*) as total_posts
            FROM posts_raw
            WHERE subreddit = ANY(:communities)
        '''), {'communities': communities})
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
    print('  3. 执行扩展语义社区抓取：python scripts/crawl_posts_semantic.py')


if __name__ == '__main__':
    asyncio.run(main())

