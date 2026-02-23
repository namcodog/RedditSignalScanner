#!/usr/bin/env python3
from __future__ import annotations

"""
Backfill full comment trees for posts in specified subreddits (full coverage).

Usage examples:
  python -u backend/scripts/backfill_comments_for_posts.py --subreddits r/Fitness,r/homegym
  python -u backend/scripts/backfill_comments_for_posts.py --csv ./高价值社区池_基于165社区.csv
  python -u backend/scripts/backfill_comments_for_posts.py --csv ./高价值社区池_基于165社区.csv --since-days 90

Notes:
  - Uses RedditAPIClient with configured rate limits and retries.
  - Persists comments idempotently and applies labels/entities.
  - Traverses posts_raw (is_current) for target subreddits; when --since-days is
    provided, only posts with created_at >= now - days are processed.
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Set
import csv
import time

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.reddit_client import RedditAPIClient
from app.services.comments_ingest import persist_comments
from app.services.labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.utils.subreddit import normalize_subreddit_name
from app.services.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore


def _read_subs_from_csv(path: Path) -> List[str]:
    subs: List[str] = []
    if not path.exists():
        return subs
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("社区名称") or row.get("name") or row.get("subreddit") or "").strip()
            if not name:
                continue
            # 过滤掉无效的社区名称（包含中文字符、冒号等）
            # 有效的社区名称应该是 r/xxx 或纯英文/数字/下划线
            if any(ord(c) > 127 for c in name):  # 包含非ASCII字符（如中文）
                continue
            if ":" in name or "：" in name:  # 包含冒号（说明性文本）
                continue
            normalized = normalize_subreddit_name(name)
            if not normalized or len(normalized) < 2:  # 太短的名称也过滤掉
                continue
            subs.append(normalized)
    return subs


async def _load_subs_from_tier(tier_alias: str) -> List[str]:
    """从 community_pool 中按 tier 读取社区列表，支持 T1/T2/T3 别名。

    示例:
      - tier_alias = \"T2\" / \"medium\" / \"silver\" → 选出所有 medium/silver 级别社区
    """
    alias = tier_alias.strip().lower()
    if not alias:
        return []

    # 支持多种写法到标准 tier 集合
    tier_map = {
        "t1": {"high", "gold", "seed", "t1", "tier1"},
        "t2": {"medium", "silver", "t2", "tier2"},
        "t3": {"semantic", "t3", "tier3"},
    }
    wanted_tiers = tier_map.get(alias, {alias})

    async with SessionFactory() as session:
        stmt = (
            select(CommunityPool.name)
            .where(
                CommunityPool.is_active.is_(True),
                CommunityPool.is_blacklisted.is_(False),
                CommunityPool.tier.in_(list(wanted_tiers)),
            )
            .order_by(CommunityPool.name)
        )
        rows = await session.execute(stmt)
        names = [normalize_subreddit_name(str(r[0])) for r in rows.fetchall() if r[0]]
    return names


async def _fetch_comments_only(
    reddit: RedditAPIClient,
    subreddit: str,
    post_id: str,
    limit_per_post: int,
    mode: str,
):
    """
    仅抓取评论，不写库（用于并发抓取）
    """
    try:
        items = await reddit.fetch_post_comments(
            post_id,
            sort="confidence",
            depth=8,
            limit=limit_per_post,
            mode=mode,
        )
        return items
    except Exception as exc:
        print(f"[ERROR] Failed to fetch comments for post={post_id} sub={subreddit}: {exc}")
        raise


async def _persist_and_label_for_post(
    session,
    subreddit: str,
    post_id: str,
    items: list,
    *,
    skip_labeling: bool = False,
) -> tuple[int, int]:
    """
    写库 + 标注（串行执行，避免锁）
    """
    try:
        if not items:
            return 0, 0

        fetched_count = len(items)
        written_count = await persist_comments(
            session, source_post_id=post_id, subreddit=subreddit, comments=items
        )

        # 在高吞吐量抓取模式下，可以跳过标注，后续批量处理
        if skip_labeling:
            print(
                f"[DEBUG] Persisted {written_count} comments for post={post_id} sub={subreddit} "
                f"(skip_labeling=True)"
            )
            return fetched_count, written_count

        ids = [c.get("id") for c in items if c.get("id")]
        await classify_and_label_comments(session, ids)
        await extract_and_label_entities_for_comments(session, ids)
        print(
            f"[DEBUG] Persisted and labeled {written_count} comments for post={post_id} sub={subreddit} "
            f"(skip_labeling=False)"
        )
        return fetched_count, written_count
    except Exception as exc:
        print(f"[ERROR] Failed to persist/label comments for post={post_id} sub={subreddit}: {exc}")
        # rollback the current transaction to avoid 'current transaction is aborted'
        try:
            await session.rollback()
        except Exception:
            pass
        raise


async def _fetch_and_persist_for_post(
    session,
    reddit: RedditAPIClient,
    subreddit: str,
    post_id: str,
    *,
    skip_labeling: bool = False,
    limit_per_post: int = 500,
    mode: str = "full",
) -> int:
    try:
        print(
            f"[DEBUG] Fetching comments for post={post_id} sub={subreddit} "
            f"mode={mode} limit={limit_per_post}"
        )
        items = await reddit.fetch_post_comments(
            post_id,
            sort="confidence",
            depth=8,
            limit=limit_per_post,
            mode=mode,
        )
        if not items:
            print(f"[DEBUG] No comments fetched for post={post_id} sub={subreddit}")
            return 0
        await persist_comments(session, source_post_id=post_id, subreddit=subreddit, comments=items)
        # 在高吞吐量抓取模式下，可以跳过标注，后续批量处理
        if skip_labeling:
            print(
                f"[DEBUG] Persisted {len(items)} comments for post={post_id} sub={subreddit} "
                f"(skip_labeling=True, mode={mode})"
            )
            return len(items)

        ids = [c.get("id") for c in items if c.get("id")]
        await classify_and_label_comments(session, ids)
        await extract_and_label_entities_for_comments(session, ids)
        print(
            f"[DEBUG] Persisted and labeled {len(items)} comments for post={post_id} sub={subreddit} "
            f"(skip_labeling=False, mode={mode})"
        )
        return len(items)
    except Exception as exc:
        print(f"[ERROR] Failed to fetch/persist comments for post={post_id} sub={subreddit}: {exc}")
        # rollback the current transaction to avoid 'current transaction is aborted'
        try:
            await session.rollback()
        except Exception:
            pass
        # re-raise to let caller handle counting/continue
        raise


async def _run(
    subreddits: Iterable[str],
    since_days: int | None,
    *,
    page_size: int = 200,
    commit_interval: int = 1,
    skip_labeling: bool = False,
    limit_per_post: int = 500,
    mode: str = "full",
    skip_existing_check: bool = False,
    use_global_limiter: bool = False,
) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    cutoff = None if since_days is None or since_days < 0 else now - timedelta(days=since_days)

    targets: Set[str] = {normalize_subreddit_name(s) for s in subreddits if s}
    if not targets:
        print("[INFO] No target subreddits resolved, nothing to do.")
        return {"processed_posts": 0, "processed_comments": 0}

    processed_posts = 0
    processed_comments = 0
    fetched_comments = 0

    # 软限流：对评论抓取请求数按分钟做平滑控制，避免短时突发超限
    import os

    soft_rate_limit_per_min = float(os.getenv("COMMENTS_SOFT_RATE_LIMIT_PER_MIN", "60"))
    soft_rate_tolerance = 1.05  # 允许 5% 的浮动
    total_fetch_calls = 0
    run_start_ts = time.monotonic()
    fetched_comments = 0

    # Build optional global limiter以协调多进程抓取。
    # 对单脚本回填场景，默认关闭全局限流，仅使用本地限流，避免 Redis 旧窗口导致长时间等待。
    limiter = None
    if use_global_limiter:
        try:
            rclient = redis.Redis.from_url(settings.reddit_cache_redis_url)
            limiter = GlobalRateLimiter(
                rclient,
                limit=max(1, int(settings.reddit_rate_limit)),
                window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
                client_id=settings.reddit_client_id or "default",
            )
        except Exception as e:
            print(f"WARN Global rate limiter init failed, fallback to local limiter: {e}")
            limiter = None

    print(
        "[INFO] Starting comments backfill: "
        f"subs={sorted(targets)}, "
        f"since_days={since_days}, "
        f"cutoff={cutoff}, "
        f"skip_labeling={skip_labeling}, "
        f"mode={mode}, "
        f"limit_per_post={limit_per_post}, "
        f"skip_existing_check={skip_existing_check}, "
        f"use_global_limiter={use_global_limiter}"
    )

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
            # 分页扫描 posts_raw，避免一次性加载全部 post_id 到内存
            offset = 0
            done = False
            commits_since = 0
            page_index = 0
            while not done:
                # 选择目标帖子：
                # - 默认模式：仅选择“当前版本且仍缺评论”的帖子，避免浪费 API 配额
                # - skip_existing_check=True：跳过 comments 聚合检查，假定这是首次大规模回填，以减少数据库压力
                if skip_existing_check:
                    if cutoff is None:
                        stmt = text(
                            """
                            SELECT source_post_id, subreddit
                            FROM posts_raw
                            WHERE is_current = TRUE
                              AND num_comments > 0
                              AND lower(subreddit) = ANY(:subs)
                            ORDER BY created_at DESC, source_post_id
                            LIMIT :limit OFFSET :offset
                            """
                        )
                        params = {"subs": [s.lower() for s in targets], "limit": page_size, "offset": offset}
                    else:
                        stmt = text(
                            """
                            SELECT source_post_id, subreddit
                            FROM posts_raw
                            WHERE is_current = TRUE
                              AND num_comments > 0
                              AND created_at >= :cutoff
                              AND lower(subreddit) = ANY(:subs)
                            ORDER BY created_at DESC, source_post_id
                            LIMIT :limit OFFSET :offset
                            """
                        )
                        params = {
                            "subs": [s.lower() for s in targets],
                            "cutoff": cutoff,
                            "limit": page_size,
                            "offset": offset,
                        }
                else:
                    if cutoff is None:
                        stmt = text(
                            """
                            WITH curr AS (
                              SELECT DISTINCT ON (source_post_id, subreddit)
                                     source_post_id, subreddit, num_comments
                              FROM posts_raw
                              WHERE is_current = TRUE AND lower(subreddit) = ANY(:subs)
                              ORDER BY source_post_id, subreddit
                            ), agg AS (
                              SELECT source_post_id, subreddit, COUNT(*) AS local_cnt
                              FROM comments
                              GROUP BY source_post_id, subreddit
                            )
                            SELECT c.source_post_id, c.subreddit, COALESCE(a.local_cnt,0) AS local_cnt
                            FROM curr c
                            LEFT JOIN agg a ON a.source_post_id=c.source_post_id AND a.subreddit=c.subreddit
                            WHERE c.num_comments > 0 AND COALESCE(a.local_cnt,0) < c.num_comments
                            ORDER BY COALESCE(a.local_cnt,0) ASC, c.subreddit, c.source_post_id
                            LIMIT :limit OFFSET :offset
                            """
                        )
                        params = {"subs": [s.lower() for s in targets], "limit": page_size, "offset": offset}
                    else:
                        stmt = text(
                            """
                            WITH curr AS (
                              SELECT DISTINCT ON (source_post_id, subreddit)
                                     source_post_id, subreddit, num_comments, created_at
                              FROM posts_raw
                              WHERE is_current = TRUE AND created_at >= :cutoff AND lower(subreddit) = ANY(:subs)
                              ORDER BY source_post_id, subreddit
                            ), agg AS (
                              SELECT source_post_id, subreddit, COUNT(*) AS local_cnt
                              FROM comments
                              GROUP BY source_post_id, subreddit
                            )
                            SELECT c.source_post_id, c.subreddit, COALESCE(a.local_cnt,0) AS local_cnt
                            FROM curr c
                            LEFT JOIN agg a ON a.source_post_id=c.source_post_id AND a.subreddit=c.subreddit
                            WHERE c.num_comments > 0 AND COALESCE(a.local_cnt,0) < c.num_comments
                            ORDER BY COALESCE(a.local_cnt,0) ASC, c.subreddit, c.source_post_id
                            LIMIT :limit OFFSET :offset
                            """
                        )
                        params = {
                            "subs": [s.lower() for s in targets],
                            "cutoff": cutoff,
                            "limit": page_size,
                            "offset": offset,
                        }

                chunk = await session.execute(stmt, params)
                rows = [(str(r[0]), str(r[1])) for r in chunk.fetchall()]
                if not rows:
                    if page_index == 0:
                        print("[INFO] No matching posts found for given filters; exiting.")
                    break

                page_index += 1
                if page_index % 5 == 1:
                    print(
                        f"[INFO] Page {page_index}: fetched {len(rows)} posts "
                        f"(offset={offset}), processed_posts={processed_posts}, "
                        f"processed_comments={processed_comments}"
                    )

                # 批量并发抓取评论（不写库）+ 串行写库
                import asyncio, random
                batch_size = int(os.getenv("COMMENTS_BACKFILL_BATCH_SIZE", "5"))

                for batch_start in range(0, len(rows), batch_size):
                    batch = rows[batch_start:batch_start + batch_size]

                    # 批次级统计（仅本批次）
                    batch_index = batch_start // batch_size + 1
                    batch_fetched = 0
                    batch_written = 0
                    batch_posts = 0

                    # 打印批次进度
                    print(
                        f"[DEBUG] Processing batch {batch_index} "
                        f"(posts {batch_start+1}-{min(batch_start+len(batch), len(rows))}/{len(rows)}) "
                        f"in page {page_index}"
                    )
                    
                    # 并发抓取评论（不写库）
                    fetch_tasks = [
                        _fetch_comments_only(reddit, sub, pid, limit_per_post, mode)
                        for pid, sub in batch
                    ]

                    # 等待所有抓取完成
                    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                    total_fetch_calls += len(batch)
                    
                    # 串行写库（避免锁）
                    for (pid, sub), result in zip(batch, fetch_results):
                        if isinstance(result, Exception):
                            print(f"[WARN] Failed to fetch comments for post={pid} sub={sub}: {result}")
                            continue
                        
                        if not result:
                            continue
                        
                        # 写库 + 标注
                        max_retries = 3
                        per_post_timeout = max(
                            30.0, float(getattr(settings, "reddit_request_timeout_seconds", 30.0)) * 2.0
                        )
                        
                        for attempt in range(max_retries):
                            try:
                                fetched, written = await asyncio.wait_for(
                                    _persist_and_label_for_post(
                                        session,
                                        sub,
                                        pid,
                                        result,
                                        skip_labeling=skip_labeling,
                                    ),
                                    timeout=per_post_timeout,
                                )
                                fetched_comments += int(fetched)
                                processed_comments += int(written)
                                processed_posts += 1
                                batch_fetched += int(fetched)
                                batch_written += int(written)
                                batch_posts += 1
                                commits_since += 1
                                if commits_since >= max(1, commit_interval):
                                    await session.commit()
                                    commits_since = 0
                                break
                            except asyncio.TimeoutError:
                                print(
                                    f"[ERROR] Timeout while persisting post={pid} sub={sub} "
                                    f"(per_post_timeout={per_post_timeout:.1f}s), skipping."
                                )
                                try:
                                    await session.rollback()
                                except Exception:
                                    pass
                                break
                            except Exception as exc:
                                msg = str(exc).lower()
                                is_deadlock = ("deadlock" in msg) or ("could not obtain lock" in msg)
                                if is_deadlock and attempt < max_retries - 1:
                                    # 针对死锁，先回滚当前事务，再退避重试
                                    try:
                                        await session.rollback()
                                    except Exception:
                                        pass
                                    await asyncio.sleep(random.uniform(0.1, 0.5))
                                    continue
                                # 其他异常也需要 rollback，避免事务停留在 aborted 状态
                                try:
                                    await session.rollback()
                                except Exception:
                                    pass
                                print(f"WARN backfill failed for post={pid} sub={sub}: {exc}")
                                break

                    # 批次总结日志，便于运维观察去重比率和实际写入
                    print(
                        f"[INFO] Page {page_index} batch {batch_index} summary: "
                        f"posts={batch_posts}, fetched_comments={batch_fetched}, "
                        f"written_comments={batch_written}"
                    )

                    # 软限流控制：若当前平均请求速率超过 soft_rate_limit_per_min，则在批次间歇性休眠
                    if soft_rate_limit_per_min > 0 and total_fetch_calls > 0:
                        elapsed = time.monotonic() - run_start_ts
                        if elapsed > 0:
                            current_per_min = total_fetch_calls / (elapsed / 60.0)
                            if current_per_min > soft_rate_limit_per_min * soft_rate_tolerance:
                                # 计算为了达到 soft_rate_limit_per_min 需要的理论耗时，并补齐差值
                                target_elapsed = total_fetch_calls * 60.0 / soft_rate_limit_per_min
                                sleep_for = max(0.0, target_elapsed - elapsed)
                                if sleep_for > 0:
                                    print(
                                        f"[INFO] Soft rate-limit active: total_fetch_calls={total_fetch_calls}, "
                                        f"current_rate={current_per_min:.2f}/min, "
                                        f"sleeping {sleep_for:.1f}s to smooth bursts"
                                    )
                                    await asyncio.sleep(sleep_for)

                # 下一页
                offset += len(rows)

            # 收尾提交
            await session.commit()

    return {
        "processed_posts": processed_posts,
        "processed_comments": processed_comments,
        "fetched_comments": fetched_comments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill full comments for posts in target subreddits")
    parser.add_argument("--subreddits", type=str, default="", help="Comma-separated subreddits like r/Fitness,r/homegym")
    parser.add_argument("--csv", type=str, default="", help="CSV path that contains a '社区名称' column")
    parser.add_argument(
        "--tier",
        type=str,
        default="",
        help="按tier从community_pool中读取社区；示例: T1/T2/T3 或 high/medium/semantic",
    )
    parser.add_argument("--since-days", type=int, default=-1, help="Only backfill posts newer than N days; use -1 for all")
    parser.add_argument("--page-size", type=int, default=200, help="Scan posts in pages to limit memory usage")
    parser.add_argument("--commit-interval", type=int, default=1, help="Commit every N posts to persist incrementally")
    parser.add_argument(
        "--skip-labeling",
        action="store_true",
        help="Only fetch and persist comments, skip NLP labeling to最大化抓取吞吐量",
    )
    parser.add_argument(
        "--limit-per-post",
        type=int,
        default=500,
        help="每个帖子抓取的最大评论数（默认500，Reddit单次上限）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "topn"],
        help="评论抓取模式：full=完整树（含 /api/morechildren），topn=仅 /comments 列表的前N条",
    )
    parser.add_argument(
        "--skip-existing-check",
        action="store_true",
        help="跳过基于 comments 表的本地评论计数检查，假定这是一轮全新大规模回填，以减少数据库聚合压力",
    )
    parser.add_argument(
        "--use-global-limiter",
        action="store_true",
        help="启用 Redis 全局限流（多进程共享配额）；默认关闭，只使用本地限流以避免旧窗口 TTL 导致长时间等待",
    )
    args = parser.parse_args()

    subs: List[str] = []
    if args.subreddits:
        subs = [normalize_subreddit_name(x.strip()) for x in args.subreddits.split(",") if x.strip()]
    elif args.csv:
        subs = _read_subs_from_csv(Path(args.csv))
    elif args.tier:
        # 按 tier 从 community_pool 中读取所有匹配社区
        subs = asyncio.run(_load_subs_from_tier(str(args.tier)))

    result = asyncio.run(
        _run(
            subs,
            args.since_days,
            page_size=max(50, args.page_size),
            commit_interval=max(1, args.commit_interval),
            skip_labeling=bool(args.skip_labeling),
            limit_per_post=max(1, min(500, int(args.limit_per_post))),
            mode=str(args.mode or "full"),
            skip_existing_check=bool(args.skip_existing_check),
            use_global_limiter=bool(args.use_global_limiter),
        )
    )
    print(result)


if __name__ == "__main__":
    main()
