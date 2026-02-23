#!/usr/bin/env python3
"""
Phase 5: 次高价值社区（15个）- 帖子+评论完整抓取
基于 crawl_posts_medium_value.py 优化版本

执行策略：
1. 帖子抓取：使用 IncrementalCrawler，12个月数据，多策略（top+new+hot）
2. 评论回填：使用 backfill_comments_for_posts.py 的逻辑

使用方法：
  python3 backend/scripts/phase5_tier2_posts_and_comments.py --mode posts
  python3 backend/scripts/phase5_tier2_posts_and_comments.py --mode comments --csv 次高价值社区池_15社区_shard1_of_3.csv
"""
import asyncio
import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.incremental_crawler import IncrementalCrawler
from app.core.config import get_settings
from app.services.global_rate_limiter import GlobalRateLimiter
from app.services.comments_ingest import persist_comments
from app.services.labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.utils.subreddit import normalize_subreddit_name, subreddit_key
import redis.asyncio as redis  # type: ignore
from sqlalchemy import text


def _read_communities_from_csv(csv_path: Path) -> list[str]:
    """从CSV读取社区列表"""
    communities = []
    if not csv_path.exists():
        return communities
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subreddit = row.get('社区名称', '').strip()
            # 跳过说明行和空行
            if subreddit and not subreddit.startswith('说明') and subreddit.startswith('r/'):
                communities.append(subreddit)
    
    return communities


async def crawl_posts_tier2(communities: list[str]) -> dict:
    """抓取次高价值社区的帖子（12个月）"""
    settings = get_settings()
    
    # 构建 Reddit 客户端
    reddit_client = RedditAPIClient(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    )

    results = []
    total_new = 0
    total_updated = 0

    async with reddit_client:
        async with SessionFactory() as db:
            crawler = IncrementalCrawler(
                db=db,
                reddit_client=reddit_client,
                hot_cache_ttl_hours=24,
            )
            
            for i, community in enumerate(communities, 1):
                print(f'\n[{i}/{len(communities)}] 抓取社区: {community}')
                
                try:
                    # 使用 time_filter='year' 抓取最近12个月
                    result = await crawler.crawl_community_incremental(
                        community_name=community,
                        limit=1000,  # 每个策略最多1000个帖子
                        time_filter='year',  # 最近12个月
                        sort='top',  # 主要策略
                    )
                    
                    new_posts = result.get('new_posts', 0)
                    updated_posts = result.get('updated_posts', 0)
                    total_new += new_posts
                    total_updated += updated_posts
                    
                    print(f'  ✅ 新增: {new_posts}, 更新: {updated_posts}')
                    results.append({
                        'community': community,
                        'new_posts': new_posts,
                        'updated_posts': updated_posts,
                        'status': 'success',
                    })
                    
                except Exception as e:
                    print(f'  ❌ 失败: {e}')
                    results.append({
                        'community': community,
                        'error': str(e),
                        'status': 'failed',
                    })
            
            await db.commit()

    return {
        'total_communities': len(communities),
        'total_new_posts': total_new,
        'total_updated_posts': total_updated,
        'results': results,
    }


async def backfill_comments_tier2(csv_path: Path, page_size: int = 200, commit_interval: int = 1) -> dict:
    """为次高价值社区回填评论"""
    communities = _read_communities_from_csv(csv_path)
    if not communities:
        return {'error': 'No communities found in CSV'}
    
    settings = get_settings()
    
    # 构建 Reddit 客户端
    reddit_client = RedditAPIClient(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    )

    processed_posts = 0
    processed_comments = 0
    
    async with reddit_client:
        async with SessionFactory() as session:
            for community in communities:
                # 查询用统一 key（去前缀+小写），避免与 posts_raw 中的存储格式大小写不一致
                sub_normalized = subreddit_key(community)
                print(f'\n📝 回填评论: {community}')
                
                # 分页查询帖子
                offset = 0
                while True:
                    result = await session.execute(
                        text('''
                            SELECT id, subreddit
                            FROM posts_raw
                            WHERE lower(subreddit) = :sub
                            AND is_current = true
                            ORDER BY created_at DESC
                            LIMIT :limit OFFSET :offset
                        '''),
                        {'sub': sub_normalized, 'limit': page_size, 'offset': offset}
                    )
                    
                    rows = result.fetchall()
                    if not rows:
                        break
                    
                    print(f'  处理 {len(rows)} 个帖子 (offset={offset})...')
                    
                    commits_since = 0
                    for pid, sub in rows:
                        try:
                            # 抓取评论
                            items = await reddit_client.fetch_post_comments(
                                pid, sort="confidence", depth=8, limit=500, mode="full"
                            )
                            
                            if items:
                                # 持久化评论
                                await persist_comments(
                                    session, source_post_id=pid, subreddit=sub, comments=items
                                )
                                
                                # 标注评论
                                ids = [c.get("id") for c in items if c.get("id")]
                                await classify_and_label_comments(session, ids)
                                await extract_and_label_entities_for_comments(session, ids)
                                
                                processed_comments += len(items)
                                processed_posts += 1
                                commits_since += 1
                                
                                # 定期提交
                                if commits_since >= commit_interval:
                                    await session.commit()
                                    commits_since = 0
                        
                        except Exception as e:
                            print(f'    ⚠️  帖子 {pid} 失败: {e}')
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                    
                    # 下一页
                    offset += len(rows)
                
                # 收尾提交
                await session.commit()
                print(f'  ✅ {community}: {processed_posts} 帖子, {processed_comments} 评论')

    return {
        'processed_posts': processed_posts,
        'processed_comments': processed_comments,
    }


async def main():
    parser = argparse.ArgumentParser(description='Phase 5: 次高价值社区帖子+评论抓取')
    parser.add_argument('--mode', choices=['posts', 'comments'], required=True, help='执行模式')
    parser.add_argument('--csv', type=str, help='CSV文件路径（comments模式必需）')
    parser.add_argument('--page-size', type=int, default=200, help='评论回填分页大小')
    parser.add_argument('--commit-interval', type=int, default=1, help='提交间隔')
    args = parser.parse_args()
    
    if args.mode == 'posts':
        # 帖子抓取模式
        csv_file = Path(__file__).parent.parent.parent / '次高价值社区池_基于165社区.csv'
        communities = _read_communities_from_csv(csv_file)
        
        print('=' * 80)
        print('Phase 5: 次高价值社区帖子抓取')
        print('=' * 80)
        print(f'社区数量: {len(communities)}')
        print(f'时间范围: 最近12个月')
        print('=' * 80)
        
        result = await crawl_posts_tier2(communities)
        
        print('\n' + '=' * 80)
        print('抓取完成')
        print('=' * 80)
        print(f'总社区数: {result["total_communities"]}')
        print(f'新增帖子: {result["total_new_posts"]:,}')
        print(f'更新帖子: {result["total_updated_posts"]:,}')
        print('=' * 80)
    
    elif args.mode == 'comments':
        # 评论回填模式
        if not args.csv:
            print('❌ 错误: comments 模式需要指定 --csv 参数')
            sys.exit(1)
        
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f'❌ 错误: CSV文件不存在: {csv_path}')
            sys.exit(1)
        
        communities = _read_communities_from_csv(csv_path)
        
        print('=' * 80)
        print('Phase 5: 次高价值社区评论回填')
        print('=' * 80)
        print(f'CSV文件: {csv_path.name}')
        print(f'社区数量: {len(communities)}')
        print(f'社区列表: {", ".join(communities)}')
        print('=' * 80)
        
        result = await backfill_comments_tier2(csv_path, args.page_size, args.commit_interval)
        
        print('\n' + '=' * 80)
        print('评论回填完成')
        print('=' * 80)
        print(f'处理帖子: {result["processed_posts"]:,}')
        print(f'回填评论: {result["processed_comments"]:,}')
        print('=' * 80)


if __name__ == '__main__':
    asyncio.run(main())
