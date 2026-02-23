#!/usr/bin/env python3
"""
历史深度抓取脚本（用于语义库构建 Stage 0.1/0.2）

特性：
- 模式 1：multi-strategy（PRAW 列表策略组合）
- 模式 2：search-partition（搜索分片：按前缀分裂，规避单链路上限）
- 从 0 开始抓取（--force-fresh 覆盖输出文件）
- 输出 JSONL（每行一个帖子对象）

用法示例：
    python backend/scripts/crawl_for_lexicon.py \
      --subreddit ecommerce \
      --target-posts 5000 \
      --output backend/data/reddit_corpus/ecommerce.jsonl \
      --force-fresh
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.reddit_client import RedditClient
from app.services.reddit_client import RedditAPIClient
from app.services.crawl.time_slicer import generate_slices, needs_split, can_split, split_slice, TimeSlice
from app.services.crawl.search_sharder import run_search_partition
from app.services.crawl.common import Submission, JSONLWriter


async def fetch_posts_deep(
    client: RedditClient,
    subreddit: str,
    target: int,
) -> List[Submission]:
    """
    使用 PRAW 深度抓取（组合多种策略）

    策略（Reddit API 限制每次最多 1000 条）：
    1. top/all: 历史热门（1000 条）
    2. top/year: 年度热门（1000 条）
    3. top/month: 月度热门（1000 条）
    4. hot: 当前热门（1000 条）
    5. new: 最新帖（1000 条）
    6. controversial/all: 争议帖（1000 条）

    去重后最多可获取 ~5000-6000 条不重复帖子
    """
    collected: List[Submission] = []
    seen_ids: Set[str] = set()

    strategies = [
        ("top/all", {"time_filter": "all", "sort": "top", "limit": 1000}),
        ("top/year", {"time_filter": "year", "sort": "top", "limit": 1000}),
        ("top/month", {"time_filter": "month", "sort": "top", "limit": 1000}),
        ("hot", {"sort": "hot", "limit": 1000}),
        ("new", {"sort": "new", "limit": 1000}),
        ("controversial/all", {"time_filter": "all", "sort": "controversial", "limit": 1000}),
    ]

    print(f"📥 开始深度抓取 r/{subreddit}（目标 {target} 帖，使用 6 种策略组合）")

    for idx, (strategy_name, params) in enumerate(strategies, 1):
        if len(collected) >= target:
            print(f"✅ 已达到目标 {target} 帖，停止抓取")
            break

        try:
            print(f"  策略 {idx}/6: {strategy_name}...")
            posts = await client.fetch_subreddit_posts(
                subreddit_name=subreddit,
                **params
            )

            new_count = 0
            for post_dict in posts:
                post_id = str(post_dict.get("id", ""))
                if not post_id or post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                collected.append(Submission.from_praw_post(post_dict))
                new_count += 1

            print(f"  策略 {idx} 完成: +{new_count} 新帖，总计 {len(collected)} 帖")

            # 每个策略之间等待 2 秒，避免触发限流
            if idx < len(strategies):
                await asyncio.sleep(2)

        except Exception as e:
            print(f"⚠️  策略 {idx} ({strategy_name}) 失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    print(f"🎉 抓取完成: 总计 {len(collected)} 帖（去重后）")
    return collected


async def fetch_time_sliced(
    subreddit: str,
    since_ts: float,
    until_ts: float,
    *,
    slice_days: int,
    min_slice_days: int,
    split_threshold: int,
    sort: str,
    client_id: str,
    client_secret: str,
    user_agent: str,
    writer: "JSONLWriter | None" = None,
    progress_path: "Path | None" = None,
) -> List[Submission]:
    """使用官方搜索 + 时间切片抓取历史帖子，并自适应二分切片。"""
    print(f"\n{'='*80}")
    print(f"🚀 开始 time-sliced 抓取")
    print(f"{'='*80}")

    api = RedditAPIClient(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        rate_limit=58,
        rate_limit_window=600.0,
        max_concurrency=2,
    )
    rows: List[Submission] = []
    seen: Set[str] = set()

    from datetime import datetime, timezone

    since = datetime.fromtimestamp(since_ts, tz=timezone.utc)
    until = datetime.fromtimestamp(until_ts, tz=timezone.utc)
    queue: List[TimeSlice] = list(generate_slices(since, until, slice_days=slice_days))

    print(f"📅 时间范围: {since.date()} 到 {until.date()}")
    print(f"📦 初始切片数: {len(queue)} 个 (每个 {slice_days} 天)")
    print(f"🎯 二分阈值: {split_threshold} 条")
    print(f"⏱️  最小切片: {min_slice_days} 天")
    print(f"{'='*80}\n")

    # 提前写入引导进度文件，便于第一时间判断是否卡在更早阶段
    if progress_path is not None:
        try:
            import json as _json, time as _time
            payload = {
                "subreddit": subreddit,
                "status": "initialized",
                "total_slices_planned": len(queue),
                "total_accumulated": 0,
                "updated_at": _time.time(),
            }
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            progress_path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    slice_count = 0
    split_count = 0

    async with api as client:
        print("🔐 正在初始化 Reddit API 客户端...")
        try:
            # 提前认证，若失败可尽早暴露
            await client.authenticate()
            print("🔑 认证成功")
        except Exception as exc:
            print(f"❌ 认证失败: {exc}")
            raise
        while queue:
            slice_count += 1
            ts = queue.pop(0)

            # 搜索该切片
            start = int(ts.start.timestamp())
            end = int(ts.end.timestamp())
            q = f"timestamp:{start}..{end}"

            print(f"\n[切片 {slice_count}] 📍 {ts.start.date()} ~ {ts.end.date()} ({ts.duration_days():.1f} 天)")
            print(f"  查询: {q}")

            after = None
            count = 0
            page_guard = 0
            page_num = 0

            # 进入切片时就写一次进度，便于观察“活跃心跳”
            if progress_path is not None:
                try:
                    import json as _json, time as _time
                    payload = {
                        "subreddit": subreddit,
                        "slice_index": slice_count,
                        "status": "running",
                        "total_accumulated": len(rows),
                        "last_slice": {
                            "start": ts.start.isoformat(),
                            "end": ts.end.isoformat(),
                            "count": 0,
                        },
                        "seen_ids": len(seen),
                        "updated_at": _time.time(),
                    }
                    progress_path.parent.mkdir(parents=True, exist_ok=True)
                    progress_path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            while True:
                page_num += 1
                print(f"  📄 第 {page_num} 页...", end=" ", flush=True)

                # 尝试多种变体以提高召回
                attempts = [
                    {"restrict_sr": 1, "syntax": "cloudsearch"},
                    {"restrict_sr": "on", "syntax": "cloudsearch"},
                    {"restrict_sr": 1, "syntax": None},
                    {"restrict_sr": "on", "syntax": None},
                ]
                posts = []
                next_after = None
                last_err = None
                for attempt in attempts:
                    try:
                        posts, next_after = await client.search_subreddit_page(
                            subreddit,
                            query=q,
                            limit=100,
                            sort=sort,
                            time_filter="all",
                            restrict_sr=attempt["restrict_sr"],
                            syntax=attempt["syntax"],
                            after=after,
                        )
                        if posts:
                            break
                    except Exception as exc:
                        last_err = exc
                        continue
                if last_err and not posts:
                    print(f"(请求失败: {last_err})")
                    break
                after = next_after

                if not posts:
                    print("(无数据)")
                    break

                new_posts = 0
                for p in posts:
                    if p.id in seen:
                        continue
                    seen.add(p.id)
                    rec = Submission(
                        id=p.id,
                        title=p.title,
                        selftext=p.selftext,
                        score=p.score,
                        num_comments=p.num_comments,
                        created_utc=float(p.created_utc),
                        subreddit=p.subreddit,
                        author=p.author,
                        url=p.url,
                        permalink=p.permalink,
                    )
                    rows.append(rec)
                    if writer is not None:
                        writer.write_record(rec)
                    count += 1
                    new_posts += 1

                print(f"获取 {len(posts)} 条 (新增 {new_posts} 条)")

                page_guard += 1
                if not after or page_guard > 1000:
                    break

            print(f"  ✅ 本切片共抓取: {count} 条 | 累计: {len(rows)} 条 (去重后)")

            # 判断是否需要二分
            if needs_split(count, split_threshold=split_threshold) and can_split(
                ts, min_slice_days=min_slice_days
            ):
                split_count += 1
                left, right = split_slice(ts)
                queue.insert(0, right)
                queue.insert(0, left)
                print(f"  🔀 触发二分 (第 {split_count} 次):")
                print(f"     左: {left.start.date()} ~ {left.end.date()} ({left.duration_days():.1f} 天)")
                print(f"     右: {right.start.date()} ~ {right.end.date()} ({right.duration_days():.1f} 天)")
                print(f"     剩余切片: {len(queue)} 个")
                continue

            # 更新进度文件
            if progress_path is not None:
                try:
                    import json as _json, time as _time
                    payload = {
                        "subreddit": subreddit,
                        "slice_index": slice_count,
                        "total_accumulated": len(rows),
                        "last_slice": {
                            "start": ts.start.isoformat(),
                            "end": ts.end.isoformat(),
                            "count": count,
                        },
                        "seen_ids": len(seen),
                        "updated_at": _time.time(),
                    }
                    progress_path.parent.mkdir(parents=True, exist_ok=True)
                    progress_path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

    print(f"\n{'='*80}")
    print(f"✅ 抓取完成！")
    print(f"{'='*80}")
    print(f"📊 统计:")
    print(f"  - 总切片数: {slice_count}")
    print(f"  - 二分次数: {split_count}")
    print(f"  - 总帖子数: {len(rows)} 条 (去重后)")
    print(f"  - 去重前: {len(seen)} 条")
    print(f"{'='*80}\n")

    return rows





async def crawl_historical_posts(
    subreddit: str,
    target_posts: int,
    output_path: str,
    force_fresh: bool = False,
) -> Dict[str, Any]:
    """使用 PRAW RedditClient 深度抓取历史帖子"""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and force_fresh:
        out.unlink()
        print(f"🗑️  已删除旧文件: {output_path}")

    from app.core.config import get_settings
    settings = get_settings()

    client = RedditClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )

    print(f"📥 开始抓取 r/{subreddit}（目标 {target_posts} 帖，使用 PRAW 深度翻页）")
    collected = await fetch_posts_deep(client, subreddit, target_posts)

    # 写入 JSONL
    with out.open("w", encoding="utf-8") as f:
        for sub in collected:
            f.write(json.dumps(asdict(sub), ensure_ascii=False) + "\n")

    stats = {
        "subreddit": subreddit,
        "total_posts": len(collected),
        "output": str(out),
    }
    print(json.dumps(stats, ensure_ascii=False))
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Historical crawl for lexicon building")
    ap.add_argument("--subreddit", required=True, help="Subreddit name without r/")
    ap.add_argument("--output", required=True)
    ap.add_argument("--force-fresh", action="store_true")
    # 模式选择
    ap.add_argument(
        "--mode",
        choices=["multi-strategy", "search-partition"],
        default="multi-strategy",
    )
    # multi-strategy 参数
    ap.add_argument("--target-posts", type=int, default=3000)
    # search-partition 参数
    ap.add_argument("--prefix-chars", default="a-z0-9", help="前缀字符集范围，如 a-z0-9")
    ap.add_argument("--max-prefix-len", type=int, default=2)
    ap.add_argument("--split-threshold", type=int, default=900)
    ap.add_argument("--max-pages-per-shard", type=int, default=15)
    ap.add_argument("--sort", default="new")
    ap.add_argument("--stream-write", action="store_true")
    args = ap.parse_args()

    try:
        subreddit = str(args.subreddit).strip()
        output = str(args.output)
        if args.mode == "multi-strategy":
            asyncio.run(
                crawl_historical_posts(
                    subreddit=subreddit,
                    target_posts=int(args.target_posts),
                    output_path=output,
                    force_fresh=bool(args.force_fresh),
                )
            )
        elif args.mode == "search-partition":
            # 搜索分片模式（避免依赖 cloudsearch timestamp）
            from app.core.config import get_settings
            settings = get_settings()
            out = Path(output)
            out.parent.mkdir(parents=True, exist_ok=True)
            writer = None
            progress_path = None
            if args.stream_write:
                if out.exists() and args.force_fresh:
                    out.unlink()
                writer = JSONLWriter(out, stream=True)
                progress_path = out.with_suffix(out.suffix + ".progress.json")
            total, kpi_path = asyncio.run(
                run_search_partition(
                    subreddit=subreddit,
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT,
                    prefix_chars=str(args.prefix_chars),
                    max_prefix_len=int(args.max_prefix_len),
                    split_threshold=int(args.split_threshold),
                    max_pages_per_shard=int(args.max_pages_per_shard),
                    sort=str(args.sort),
                    writer=writer,
                    progress_path=progress_path,
                    kpi_output_dir=out.parent,
                )
            )
            # 一次性落盘（未开启流）
            if not args.stream_write:
                # run_search_partition 在未提供 writer 时不会返回记录集合，主张全部流式
                # 为保持一致性，这里只输出 KPI 路径与总量
                pass
            import json as _json
            print(_json.dumps({
                "subreddit": subreddit,
                "total_posts": int(total),
                "output": output,
                "progress": str(progress_path) if progress_path else None,
                "kpi": str(kpi_path),
            }, ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
