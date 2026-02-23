#!/usr/bin/env python3
from __future__ import annotations

"""
改进版：支持水位线、断点续抓、指数退避重试的Reddit帖子抓取脚本

新增功能：
1. ✅ 水位线支持：避免重复抓取已有数据
2. ✅ 断点续抓：中断后可从上次位置继续
3. ✅ 指数退避重试：提高API调用成功率
4. ✅ 进度实时保存：每个切片完成后保存进度
5. ✅ 详细日志：记录每个步骤的执行情况

使用示例：
  # 基础用法（与v1相同）
  python -u backend/scripts/crawl_posts_from_csv_v2.py --csv 次高价值社区_15社区_shard1_of_3.csv --since 2024-01 --until 2025-01
  
  # 启用水位线（推荐）
  python -u backend/scripts/crawl_posts_from_csv_v2.py --csv xxx.csv --since 2024-01 --until 2025-01 --use-watermark
  
  # 断点续抓（自动检测进度文件）
  python -u backend/scripts/crawl_posts_from_csv_v2.py --csv xxx.csv --since 2024-01 --until 2025-01 --resume
  
  # 完整功能（推荐）
  python -u backend/scripts/crawl_posts_from_csv_v2.py \
    --csv 次高价值社区_15社区_shard1_of_3.csv \
    --since 2024-01 --until 2025-01 \
    --use-watermark --resume --safe --dedupe
"""

import argparse
import asyncio
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient
from app.utils.subreddit import normalize_subreddit_name
from app.services.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore


def _read_csv(path: Path) -> List[str]:
    """从CSV文件读取社区列表"""
    headers: Sequence[str] = []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        rows = list(r)
    name_col = next((c for c in ("社区名称", "subreddit", "name") if c in headers), None)
    if not name_col:
        raise ValueError("CSV must contain a '社区名称' (or 'subreddit'/'name') column")
    subs: List[str] = []
    for row in rows:
        v = (row.get(name_col) or "").strip()
        if not v:
            continue
        subs.append(v)
    return subs


def _build_month_slices_from_months(months: int) -> List[tuple[int, int]]:
    """构建月度时间切片（最近N个月）"""
    now = datetime.now(timezone.utc)
    start_month = (now.month - (months - 1) - 1) % 12 + 1
    start_year = now.year + ((now.month - (months - 1) - 1) // 12)
    cur = datetime(start_year, start_month, 1, tzinfo=timezone.utc)
    slices: List[tuple[int, int]] = []
    for _ in range(months):
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        slices.append((int(cur.timestamp()), int((nxt - timedelta(seconds=1)).timestamp())))
        cur = nxt
    return slices


def _build_month_slices_since_until(since: str, until: str) -> List[tuple[int, int]]:
    """构建月度时间切片（指定时间范围）"""
    def to_dt(ym: str) -> datetime:
        return datetime.strptime(ym + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    cur = to_dt(since)
    end = to_dt(until)
    if end.month == 12:
        end_next = end.replace(year=end.year + 1, month=1)
    else:
        end_next = end.replace(month=end.month + 1)
    slices: List[tuple[int, int]] = []
    while cur < end_next:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        slices.append((int(cur.timestamp()), int((nxt - timedelta(seconds=1)).timestamp())))
        cur = nxt
    return slices


def _chunk(seq, size):
    """将序列分块"""
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


@dataclass
class CrawlProgress:
    """抓取进度记录"""
    subreddit: str
    last_completed_slice_idx: int
    total_slices: int
    completed: bool
    total_posts: int
    total_new: int
    total_updated: int
    total_duplicates: int
    last_updated: str


class ProgressManager:
    """进度管理器：支持断点续抓"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.progress: Dict[str, CrawlProgress] = {}
        self._load()
    
    def _load(self):
        """加载进度文件"""
        if self.progress_file.exists():
            with open(self.progress_file, "r") as f:
                data = json.load(f)
                for sub, info in data.items():
                    self.progress[sub] = CrawlProgress(**info)
            print(f"✅ 加载进度文件: {len(self.progress)} 个社区")
    
    def _save(self):
        """保存进度文件"""
        data = {sub: vars(prog) for sub, prog in self.progress.items()}
        with open(self.progress_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_progress(self, subreddit: str, total_slices: int) -> CrawlProgress:
        """获取社区的抓取进度"""
        if subreddit not in self.progress:
            self.progress[subreddit] = CrawlProgress(
                subreddit=subreddit,
                last_completed_slice_idx=-1,
                total_slices=total_slices,
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
        slice_idx: int,
        posts: int,
        new: int,
        updated: int,
        duplicates: int,
        completed: bool = False,
    ):
        """更新进度"""
        prog = self.progress[subreddit]
        prog.last_completed_slice_idx = slice_idx
        prog.total_posts += posts
        prog.total_new += new
        prog.total_updated += updated
        prog.total_duplicates += duplicates
        prog.completed = completed
        prog.last_updated = datetime.now(timezone.utc).isoformat()
        self._save()
    
    def is_completed(self, subreddit: str) -> bool:
        """检查社区是否已完成"""
        return self.progress.get(subreddit, CrawlProgress("", -1, 0, False, 0, 0, 0, 0, "")).completed


async def fetch_with_retry(func, max_retries: int = 3, base_delay: float = 1.0):
    """带指数退避的重试机制"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # 指数退避 + 随机抖动
            wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
            print(f"   ⚠️ 重试 {attempt+1}/{max_retries} (等待 {wait_time:.2f}s): {e}")
            await asyncio.sleep(wait_time)


async def get_watermark(session: AsyncSession, community_name: str) -> Optional[datetime]:
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
    slices: List[tuple[int, int]],
    per_slice_max: int,
    safe_mode: bool,
    use_timestamp_slice: bool,
    dedupe: bool,
    ingest_batch_size: int,
    max_subs: int | None,
    use_watermark: bool,
    resume: bool,
    progress_file: Path,
    max_retries: int,
) -> dict:
    """改进版抓取逻辑"""
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

                # 获取进度
                progress = progress_mgr.get_progress(name, len(slices)) if progress_mgr else None
                start_slice_idx = progress.last_completed_slice_idx + 1 if progress else 0

                if progress and start_slice_idx > 0:
                    print(f"🔄 断点续抓: 从切片 {start_slice_idx}/{len(slices)} 继续")

                try:
                    seen: set[str] = set() if dedupe else set()
                    sub_new = sub_upd = sub_dup = sub_total = 0

                    for slice_idx, (start_ts, end_ts) in enumerate(slices[start_slice_idx:], start=start_slice_idx):
                        # 格式化时间范围
                        start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                        end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
                        slice_label = f"{start_dt.strftime('%Y-%m')} ~ {end_dt.strftime('%Y-%m')}"

                        # 检查水位线：如果切片结束时间早于水位线，跳过
                        if watermark and end_dt < watermark:
                            print(f"   ⏭️  切片 {slice_idx+1}/{len(slices)} ({slice_label}): 跳过（早于水位线）")
                            if progress_mgr:
                                progress_mgr.update_progress(name, slice_idx, 0, 0, 0, 0)
                            continue

                        print(f"   📥 切片 {slice_idx+1}/{len(slices)} ({slice_label}): 抓取中...")

                        # 带重试的抓取：单窗口模式改用 fetch_subreddit_posts + 本地时间过滤，避免 timestamp API 空跑
                        async def fetch_slice():
                            if use_timestamp_slice:
                                return await reddit.fetch_subreddit_posts_by_timestamp(
                                    subreddit=raw,
                                    start_epoch=start_ts,
                                    end_epoch=end_ts,
                                    sort="new",
                                    max_posts=min(per_slice_max, 200 if safe_mode else per_slice_max),
                                )
                            posts, _ = await reddit.fetch_subreddit_posts(
                                raw,
                                limit=min(per_slice_max, 100),  # Reddit API 上限 100
                                time_filter="year",
                                sort="new",
                            )
                            return posts

                        batch = await fetch_with_retry(fetch_slice, max_retries=max_retries)

                        if not batch:
                            print(f"   ⚠️  切片 {slice_idx+1}/{len(slices)}: 无数据")
                            if progress_mgr:
                                progress_mgr.update_progress(name, slice_idx, 0, 0, 0, 0)
                            continue

                        # 按窗口+水位线过滤
                        filtered = []
                        for p in batch:
                            p_dt = datetime.fromtimestamp(p.created_utc, tz=timezone.utc)
                            if p_dt < start_dt or p_dt > end_dt:
                                continue
                            if watermark and p_dt <= watermark:
                                continue
                            filtered.append(p)

                        # 内存去重
                        use_list = filtered if not dedupe else [p for p in filtered if p.id not in seen]
                        if dedupe:
                            for p in use_list:
                                seen.add(p.id)

                        slice_posts = len(use_list)
                        sub_total += slice_posts
                        total_posts_fetched += slice_posts

                        # 批量写入数据库
                        slice_new = slice_upd = slice_dup = 0
                        if use_list:
                            for part in _chunk(use_list, max(10, ingest_batch_size)):
                                res = await crawler.ingest_posts_batch(name, part)
                                slice_new += res.get("new", 0)
                                slice_upd += res.get("updated", 0)
                                slice_dup += res.get("duplicates", 0)

                        sub_new += slice_new
                        sub_upd += slice_upd
                        sub_dup += slice_dup

                        print(f"   ✅ 切片 {slice_idx+1}/{len(slices)}: 新增={slice_new}, 更新={slice_upd}, 去重={slice_dup}, 总计={slice_posts}")

                        # 更新进度
                        if progress_mgr:
                            progress_mgr.update_progress(
                                name, slice_idx, slice_posts, slice_new, slice_upd, slice_dup
                            )

                        # 释放内存
                        del batch
                        del use_list
                        import gc as _gc
                        _gc.collect()

                    # 标记完成
                    if progress_mgr:
                        progress_mgr.update_progress(name, len(slices) - 1, 0, 0, 0, 0, completed=True)

                    total_new += sub_new
                    total_updated += sub_upd
                    total_dups += sub_dup
                    processed_subs += 1

                    print(f"\n✅ r/{raw} 完成: 新增={sub_new}, 更新={sub_upd}, 去重={sub_dup}, 总帖子={sub_total}")

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
    parser = argparse.ArgumentParser(
        description="改进版：支持水位线、断点续抓、指数退避重试的Reddit帖子抓取脚本"
    )
    parser.add_argument("--csv", type=str, default="", help="CSV文件路径")
    parser.add_argument("--subs", type=str, default="", help="逗号分隔的社区列表")
    parser.add_argument("--months", type=int, default=12, help="回溯月数（默认12）")
    parser.add_argument("--since", type=str, default="", help="开始时间 YYYY-MM")
    parser.add_argument("--until", type=str, default="", help="结束时间 YYYY-MM")
    parser.add_argument("--per-slice", type=int, default=1000, help="每个切片最大帖子数")
    parser.add_argument("--safe", action="store_true", help="安全模式（低并发）")
    parser.add_argument("--dedupe", action="store_true", help="启用内存去重")
    parser.add_argument("--ingest-batch", type=int, default=50, help="数据库批量写入大小")
    parser.add_argument("--max-subs", type=int, default=0, help="最多处理N个社区（0=全部）")
    parser.add_argument("--use-watermark", action="store_true", help="✅ 启用水位线（推荐）")
    parser.add_argument("--resume", action="store_true", help="✅ 启用断点续抓（推荐）")
    parser.add_argument("--progress-file", type=str, default="crawl_progress.json", help="进度文件路径")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")
    parser.add_argument("--single-window", action="store_true", help="单窗口抓取（不按月切片），适合低活跃探针")

    args = parser.parse_args()

    # 读取社区列表
    subs: List[str] = []
    if args.csv:
        subs = _read_csv(Path(args.csv))
    elif args.subs:
        subs = [s.strip() for s in args.subs.split(",") if s.strip()]
    else:
        raise SystemExit("必须指定 --csv 或 --subs")

    # 构建时间切片（默认按月；single-window 时仅一个窗口）
    if args.single_window:
        now = datetime.now(timezone.utc)
        if args.since and args.until:
            start = datetime.strptime(args.since + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(args.until + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if end.month == 12:
                end = end.replace(year=end.year + 1, month=1)
            else:
                end = end.replace(month=end.month + 1)
        else:
            months = max(1, int(args.months))
            start = now - timedelta(days=30 * months)
            end = now
        slices = [(int(start.timestamp()), int(end.timestamp()))]
    else:
        if args.since and args.until:
            slices = _build_month_slices_since_until(args.since, args.until)
        else:
            slices = _build_month_slices_from_months(max(1, int(args.months)))

    print(f"\n{'='*60}")
    print(f"🚀 改进版Reddit抓取脚本 v2.0")
    print(f"{'='*60}")
    print(f"📋 社区数量: {len(subs)}")
    print(f"📅 时间切片: {len(slices)}{' (单窗口)' if args.single_window else ' 个月'}")
    print(f"✅ 水位线: {'启用' if args.use_watermark else '禁用'}")
    print(f"✅ 断点续抓: {'启用' if args.resume else '禁用'}")
    print(f"✅ 指数退避: 最大重试 {args.max_retries} 次")
    print(f"{'='*60}\n")

    result = asyncio.run(
        _run(
            subs,
            slices=slices,
            per_slice_max=max(100, int(args.per_slice)),
            safe_mode=bool(args.safe),
            use_timestamp_slice=not bool(args.single_window),
            dedupe=bool(args.dedupe),
            ingest_batch_size=max(10, int(args.ingest_batch)),
            max_subs=(int(args.max_subs) if int(args.max_subs) > 0 else None),
            use_watermark=bool(args.use_watermark),
            resume=bool(args.resume),
            progress_file=Path(args.progress_file),
            max_retries=int(args.max_retries),
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
