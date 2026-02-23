#!/usr/bin/env python3
"""
使用/new端点抓取Reddit帖子（支持分片并发）

与timestamp搜索不同，这个脚本使用Reddit的/new端点，
该端点更可靠但有1000帖子的限制。

特点：
1. ✅ 使用/new端点（更可靠）
2. ✅ 支持水位线（避免重复抓取）
3. ✅ 支持断点续抓
4. ✅ 支持分片并发
5. ✅ 指数退避重试

限制：
- 每个社区最多抓取1000个帖子（Reddit API限制）
- 适合增量抓取，不适合历史回填

使用示例：
  # 基础用法
  python backend/scripts/crawl_posts_new_endpoint.py --csv 社区列表.csv
  
  # 完整功能
  python backend/scripts/crawl_posts_new_endpoint.py \
    --csv 次高价值社区_15社区_shard1_of_3.csv \
    --time-filter month \
    --max-posts 1000 \
    --use-watermark \
    --resume \
    --safe
"""

import argparse
import asyncio
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient
from app.utils.subreddit import normalize_subreddit_name
from app.services.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis


def _read_csv(path: Path) -> List[str]:
    """从CSV文件读取社区列表"""
    headers = []
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        rows = list(r)
    name_col = next((c for c in ("社区名称", "subreddit", "name") if c in headers), None)
    if not name_col:
        raise ValueError("CSV must contain a '社区名称' (or 'subreddit'/'name') column")
    subs = []
    for row in rows:
        v = (row.get(name_col) or "").strip()
        if not v:
            continue
        # 跳过说明/策略等非社区行（常见于“说明：这15个社区...”）
        if v.startswith("说明") or v.startswith("抓取策略"):
            continue
        subs.append(v)
    return subs


@dataclass
class CrawlProgress:
    """抓取进度记录"""
    subreddit: str
    completed: bool
    total_posts: int
    total_new: int
    total_updated: int
    total_duplicates: int
    last_updated: str


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.progress: Dict[str, CrawlProgress] = {}
        self._load()
    
    def _load(self):
        if self.progress_file.exists():
            with open(self.progress_file, "r") as f:
                data = json.load(f)
                for sub, info in data.items():
                    self.progress[sub] = CrawlProgress(**info)
            print(f"✅ 加载进度文件: {len(self.progress)} 个社区")
    
    def _save(self):
        data = {sub: vars(prog) for sub, prog in self.progress.items()}
        with open(self.progress_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_progress(self, subreddit: str) -> CrawlProgress:
        if subreddit not in self.progress:
            self.progress[subreddit] = CrawlProgress(
                subreddit=subreddit,
                completed=False,
                total_posts=0,
                total_new=0,
                total_updated=0,
                total_duplicates=0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
        return self.progress[subreddit]
    
    def update_progress(
        self,
        subreddit: str,
        posts: int,
        new: int,
        updated: int,
        duplicates: int,
        completed: bool = False,
    ):
        # 确保进度记录存在
        prog = self.get_progress(subreddit)
        prog.total_posts += posts
        prog.total_new += new
        prog.total_updated += updated
        prog.total_duplicates += duplicates
        prog.completed = completed
        prog.last_updated = datetime.now(timezone.utc).isoformat()
        self._save()
    
    def is_completed(self, subreddit: str) -> bool:
        return self.progress.get(subreddit, CrawlProgress("", False, 0, 0, 0, 0, "")).completed


async def fetch_with_retry(func, max_retries: int = 3, base_delay: float = 1.0):
    """带指数退避的重试机制"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
            print(f"   ⚠️ 重试 {attempt+1}/{max_retries} (等待 {wait_time:.2f}s): {e}")
            await asyncio.sleep(wait_time)


async def get_watermark(session, community_name: str) -> Optional[datetime]:
    """获取社区的水位线"""
    result = await session.execute(
        select(CommunityCache.last_seen_created_at).where(
            CommunityCache.community_name == community_name
        )
    )
    watermark = result.scalar_one_or_none()
    return watermark


async def _run(
    subs: Iterable[str],
    *,
    time_filter: str,
    max_posts: int,
    safe_mode: bool,
    use_watermark: bool,
    resume: bool,
    progress_file: Path,
    max_retries: int,
    max_subs: int | None,
) -> dict:
    """改进版抓取逻辑（使用/new端点）"""
    settings = get_settings()

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
        print("✅ 全局限流器初始化成功")
    except Exception as e:
        print(f"⚠️ 全局限流器初始化失败: {e}")

    # 初始化进度管理器
    progress_mgr = ProgressManager(progress_file) if resume else None
    if progress_mgr:
        print(f"✅ 断点续抓模式：进度文件 {progress_file}")

    processed_subs = 0
    total_posts_fetched = 0
    total_new = 0
    total_updated = 0
    total_dups = 0

    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=min(settings.reddit_max_concurrency, 2 if safe_mode else settings.reddit_max_concurrency),
        global_rate_limiter=limiter,
    ) as reddit:
        # 使用async with正确管理session
        async with SessionFactory() as session:
            crawler = IncrementalCrawler(session, reddit, hot_cache_ttl_hours=24)
            
            for name in subs:
                raw = normalize_subreddit_name(name)
                
                # 检查是否已完成
                if progress_mgr and progress_mgr.is_completed(name):
                    print(f"⏭️  跳过 r/{raw} (已完成)")
                    continue
                
                print(f"\n{'='*60}")
                print(f"🚀 开始抓取: r/{raw}")
                print(f"{'='*60}")
                
                # 获取水位线
                watermark = None
                if use_watermark:
                    watermark = await get_watermark(session, name)
                    if watermark:
                        print(f"📍 水位线: {watermark.isoformat()}")
                    else:
                        print(f"📍 水位线: 无（首次抓取）")
                
                try:
                    # 使用/new端点抓取
                    print(f"   📥 使用/new端点抓取 (time_filter={time_filter}, max={max_posts})...")
                    
                    async def fetch_posts():
                        return await reddit.fetch_subreddit_posts_paginated(
                            subreddit=raw,
                            time_filter=time_filter,
                            sort="new",
                            max_posts=max_posts
                        )
                    
                    batch = await fetch_with_retry(fetch_posts, max_retries=max_retries)
                    
                    if not batch:
                        print(f"   ⚠️  无数据")
                        if progress_mgr:
                            progress_mgr.update_progress(name, 0, 0, 0, 0, completed=True)
                        continue
                    
                    # 水位线过滤
                    if watermark:
                        original_count = len(batch)
                        batch = [
                            p for p in batch
                            if datetime.fromtimestamp(p.created_utc, tz=timezone.utc) > watermark
                        ]
                        filtered_count = original_count - len(batch)
                        if filtered_count > 0:
                            print(f"   🔍 水位线过滤: {filtered_count} 个旧帖子")
                    
                    posts_count = len(batch)
                    total_posts_fetched += posts_count
                    
                    # 批量写入数据库
                    sub_new = sub_upd = sub_dup = 0
                    if batch:
                        res = await crawler.ingest_posts_batch(name, batch)
                        sub_new = res.get("new", 0)
                        sub_upd = res.get("updated", 0)
                        sub_dup = res.get("duplicates", 0)
                    
                    total_new += sub_new
                    total_updated += sub_upd
                    total_dups += sub_dup
                    
                    print(f"   ✅ 完成: 新增={sub_new}, 更新={sub_upd}, 去重={sub_dup}, 总计={posts_count}")
                    
                    # 更新进度
                    if progress_mgr:
                        progress_mgr.update_progress(
                            name, posts_count, sub_new, sub_upd, sub_dup, completed=True
                        )
                    
                    processed_subs += 1
                    
                    if max_subs and processed_subs >= max_subs:
                        break
                
                except Exception as e:
                    print(f"\n❌ r/{raw} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
    
    return {
        "processed_subs": processed_subs,
        "posts_fetched": total_posts_fetched,
        "new": total_new,
        "updated": total_updated,
        "duplicates": total_dups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="使用/new端点抓取Reddit帖子（支持分片并发）")
    parser.add_argument("--csv", type=str, required=True, help="CSV文件路径")
    parser.add_argument("--time-filter", type=str, default="month", 
                       choices=["hour", "day", "week", "month", "year", "all"],
                       help="时间过滤器（默认month）")
    parser.add_argument("--max-posts", type=int, default=1000, help="每个社区最大帖子数（默认1000）")
    parser.add_argument("--safe", action="store_true", help="安全模式（低并发）")
    parser.add_argument("--use-watermark", action="store_true", help="✅ 启用水位线（推荐）")
    parser.add_argument("--resume", action="store_true", help="✅ 启用断点续抓（推荐）")
    parser.add_argument("--progress-file", type=str, default="crawl_progress_new.json", help="进度文件路径")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")
    parser.add_argument("--max-subs", type=int, default=0, help="最多处理N个社区（0=全部）")
    
    args = parser.parse_args()
    
    subs = _read_csv(Path(args.csv))
    
    print(f"\n{'='*60}")
    print(f"🚀 Reddit抓取脚本（/new端点）")
    print(f"{'='*60}")
    print(f"📋 社区数量: {len(subs)}")
    print(f"📅 时间过滤: {args.time_filter}")
    print(f"📊 每社区最大: {args.max_posts} 帖子")
    print(f"✅ 水位线: {'启用' if args.use_watermark else '禁用'}")
    print(f"✅ 断点续抓: {'启用' if args.resume else '禁用'}")
    print(f"✅ 指数退避: 最大重试 {args.max_retries} 次")
    print(f"{'='*60}\n")
    
    result = asyncio.run(
        _run(
            subs,
            time_filter=args.time_filter,
            max_posts=args.max_posts,
            safe_mode=bool(args.safe),
            use_watermark=bool(args.use_watermark),
            resume=bool(args.resume),
            progress_file=Path(args.progress_file),
            max_retries=int(args.max_retries),
            max_subs=(int(args.max_subs) if int(args.max_subs) > 0 else None),
        )
    )
    
    print(f"\n{'='*60}")
    print(f"✅ 抓取完成！")
    print(f"{'='*60}")
    print(f"📊 处理社区: {result['processed_subs']}")
    print(f"📊 抓取帖子: {result['posts_fetched']}")
    print(f"📊 新增帖子: {result['new']}")
    print(f"📊 更新帖子: {result['updated']}")
    print(f"📊 去重帖子: {result['duplicates']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
