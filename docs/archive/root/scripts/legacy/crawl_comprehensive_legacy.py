#!/usr/bin/env python3
"""
[LEGACY] 多策略全量抓取脚本 (帖子 + 评论)

支持三种模式：
1. 只抓帖子（默认）：使用 top + new + hot 三种排序策略
2. 只抓评论（--comments-only）：跳过帖子，直接补齐评论数据
3. 帖子+评论（--with-comments）：抓完帖子后自动抓取评论

用法:
    # 只抓帖子
    python3 backend/scripts/crawl_comprehensive.py --scope all

    # 只抓评论
    python3 backend/scripts/crawl_comprehensive.py --scope all --comments-only

    # 帖子+评论一起抓
    python3 backend/scripts/crawl_comprehensive.py --scope all --with-comments
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Set

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.community_pool_loader import CommunityPoolLoader
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient
from app.services.comments_ingest import persist_comments
from app.utils.subreddit import subreddit_key, normalize_subreddit_name
from sqlalchemy import text
from app.services.crawl.crawl_plan import CrawlPlanBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(description="多策略全量抓取 Reddit 帖子和评论")
    parser.add_argument(
        "--scope",
        choices=["all", "crossborder", "high", "medium", "low"],
        help="抓取范围：all=所有活跃社区, crossborder=跨境电商社区, high/medium/low=按优先级",
    )
    parser.add_argument(
        "--communities",
        nargs="+",
        help="指定社区列表（如 r/Entrepreneur r/ecommerce）",
    )
    parser.add_argument(
        "--time-filter",
        default="all",
        choices=["hour", "day", "week", "month", "year", "all"],
        help="时间范围（默认 all）",
    )
    parser.add_argument(
        "--max-per-strategy",
        type=int,
        default=1000,
        help="每种策略最多抓取的帖子数（默认 1000）",
    )
    parser.add_argument(
        "--ignore-watermark",
        action="store_true",
        default=True,
        help="忽略水位线，强制重新抓取所有历史数据（默认 True）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出结果到 JSON 文件",
    )
    # 评论回填参数
    parser.add_argument(
        "--with-comments",
        action="store_true",
        help="抓完帖子后自动抓取评论",
    )
    parser.add_argument(
        "--comments-only",
        action="store_true",
        help="跳过帖子抓取，只抓取评论（用于补齐评论数据）",
    )
    parser.add_argument(
        "--comments-limit-per-post",
        type=int,
        default=500,
        help="每个帖子最多抓取的评论数（默认 500，Reddit API 上限）",
    )
    parser.add_argument(
        "--comments-page-size",
        type=int,
        default=100,
        help="评论回填时每批次处理的帖子数（默认 100）",
    )
    parser.add_argument(
        "--skip-labeling",
        action="store_true",
        help="跳过评论 NLP 标注，专注抓取（推荐大规模回填时开启）",
    )

    args = parser.parse_args()

    if not args.scope and not args.communities:
        parser.error("必须指定 --scope 或 --communities")

    settings = get_settings()

    # 初始化 Reddit 客户端
    reddit_client = RedditAPIClient(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        max_concurrency=settings.reddit_max_concurrency,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
    )

    try:
        # 获取社区列表（短生命周期 Session，避免长事务污染）
        async with SessionFactory() as db:
            plan_builder = CrawlPlanBuilder(db)
            plan_entries = await plan_builder.build_plan()

            def _match_scope(entry: Any) -> bool:
                if entry.status != "active":
                    return False
                if args.scope == "all" or args.scope is None:
                    return True
                if args.scope == "crossborder":
                    return any(
                        str(cat).lower() == "crossborder" for cat in entry.profile.categories
                    )
                if args.scope in {"high", "medium", "low"}:
                    return (entry.priority or "").lower() == args.scope
                return True

            # posts 用计划里 crawl_track != none/ comments_only
            planned_posts = [
                entry
                for entry in plan_entries
                if _match_scope(entry) and entry.crawl_track not in {"none", "comments_only"}
            ]
            # comments 用计划里 crawl_track != none/ posts_only
            planned_comments = [
                entry
                for entry in plan_entries
                if _match_scope(entry) and entry.crawl_track not in {"none", "posts_only"}
            ]

            # 若指定 communities，则按计划过滤
            if args.communities:
                wanted = {normalize_subreddit_name(c) for c in args.communities}
                planned_posts = [
                    e for e in planned_posts if normalize_subreddit_name(e.profile.name) in wanted
                ]
                planned_comments = [
                    e for e in planned_comments if normalize_subreddit_name(e.profile.name) in wanted
                ]
                logger.info(f"📋 指定社区: {len(wanted)} 个，命中计划：posts={len(planned_posts)}, comments={len(planned_comments)}")

            communities_posts = [e.profile.name for e in planned_posts]
            communities_comments = [e.profile.name for e in planned_comments]

            # 根据模式决定是否需要社区列表
            need_posts = not args.comments_only
            need_comments = args.with_comments or args.comments_only

            if need_posts and not communities_posts:
                logger.warning("⚠️ 没有符合条件的社区用于帖子抓取")
            if need_comments and not communities_comments:
                logger.warning("⚠️ 没有符合条件的社区用于评论回填")

            logger.info(
                f"📋 加载社区(计划) posts={len(communities_posts)}, comments={len(communities_comments)}, scope={args.scope}"
            )

        if need_posts and not communities_posts and not need_comments:
            logger.warning("⚠️ 没有找到符合条件的社区（帖子抓取）")
            return
        if need_comments and not communities_comments and not need_posts:
            logger.warning("⚠️ 没有找到符合条件的社区（评论回填）")
            return
        if need_posts and not communities_posts and need_comments and not communities_comments:
            logger.warning("⚠️ 没有找到符合条件的社区（帖子与评论均为空）")
            return

        # ============================================================
        # 阶段 1：帖子抓取（除非 --comments-only）
        # ============================================================
        posts_summary = None
        if not args.comments_only:
            logger.info(f"🚀 开始多策略抓取 {len(communities_posts)} 个社区的帖子...")
            logger.info(f"⚙️ 配置: time_filter={args.time_filter}, max_per_strategy={args.max_per_strategy}")
            
            results: list[dict[str, Any]] = []
            total_new = 0
            total_updated = 0
            total_duplicates = 0
            total_fetched = 0
            succeeded = 0
            failed = 0

            for i, community in enumerate(communities_posts, 1):
                logger.info(f"\n{'='*80}")
                logger.info(f"[{i}/{len(communities_posts)}] 抓取社区: {community}")
                logger.info(f"{'='*80}")

                async with SessionFactory() as db:
                    crawler = IncrementalCrawler(
                        db=db,
                        reddit_client=reddit_client,
                        hot_cache_ttl_hours=48,
                        source_track="backfill_posts",
                    )

                    result = await crawler.crawl_community_comprehensive(
                        community_name=community,
                        time_filter=args.time_filter,
                        max_per_strategy=args.max_per_strategy,
                        ignore_watermark=args.ignore_watermark,
                    )
                    await db.commit()

                    # 诊断：确认当前连接目标以及写入可见性
                    diag_row = (
                        await db.execute(
                            text(
                                "select current_database() as db, current_user as usr, "
                                "inet_server_addr() as host, inet_server_port() as port"
                            )
                        )
                    ).mappings().first()
                    cnt_row = (
                        await db.execute(
                            text(
                                "select count(*) as cnt, max(fetched_at) as max_fetched "
                                "from posts_raw where subreddit = :sub"
                            ),
                            {"sub": subreddit_key(community)},
                        )
                    ).mappings().first()
                    logger.info(
                        "🧪 DB diag: db=%s user=%s host=%s port=%s | posts_raw[%s]: count=%s, max_fetched=%s",
                        diag_row.get("db"),
                        diag_row.get("usr"),
                        diag_row.get("host"),
                        diag_row.get("port"),
                        subreddit_key(community),
                        cnt_row.get("cnt"),
                        cnt_row.get("max_fetched"),
                    )

                results.append(result)

                if "error" in result:
                    failed += 1
                    logger.error(f"❌ {community}: {result['error']}")
                else:
                    succeeded += 1
                    total_new += result["new_posts"]
                    total_updated += result["updated_posts"]
                    total_duplicates += result["duplicates"]
                    total_fetched += result["total_fetched"]
                    
                    logger.info(
                        f"✅ {community}: "
                        f"新增={result['new_posts']}, "
                        f"更新={result['updated_posts']}, "
                        f"去重={result['duplicates']}, "
                        f"总获取={result['total_fetched']}, "
                        f"耗时={result['duration_seconds']:.2f}s"
                    )

            # 汇总统计
            logger.info(f"\n{'='*80}")
            logger.info("📊 帖子抓取完成！汇总统计：")
            logger.info(f"{'='*80}")
            logger.info(f"总社区数: {len(communities_posts)}")
            logger.info(f"成功: {succeeded}")
            logger.info(f"失败: {failed}")
            logger.info(f"新增帖子: {total_new}")
            logger.info(f"更新帖子: {total_updated}")
            logger.info(f"去重帖子: {total_duplicates}")
            logger.info(f"总获取帖子: {total_fetched}")
            logger.info(f"平均每社区: {total_fetched / len(communities_posts):.1f} 个帖子")

            posts_summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scope": args.scope or "custom",
                "time_filter": args.time_filter,
                "max_per_strategy": args.max_per_strategy,
                "total_communities": len(communities_posts),
                "succeeded": succeeded,
                "failed": failed,
                "total_new_posts": total_new,
                "total_updated_posts": total_updated,
                "total_duplicates": total_duplicates,
                "total_fetched": total_fetched,
                "avg_posts_per_community": total_fetched / len(communities_posts) if communities_posts else 0,
                "communities": results,
            }

        # ============================================================
        # 阶段 2：评论回填（如果 --with-comments 或 --comments-only）
        # ============================================================
        comments_summary = None
        if args.with_comments or args.comments_only:
            logger.info(f"\n{'='*80}")
            logger.info(f"💬 开始评论回填 {len(communities_comments)} 个社区...")
            logger.info(f"⚙️ 配置: limit_per_post={args.comments_limit_per_post}, page_size={args.comments_page_size}, skip_labeling={args.skip_labeling}")
            logger.info(f"{'='*80}")

            targets: Set[str] = {normalize_subreddit_name(c) for c in communities_comments if c}
            processed_posts = 0
            processed_comments = 0
            soft_rate_limit_per_min = float(os.getenv("COMMENTS_SOFT_RATE_LIMIT_PER_MIN", "40"))
            total_fetch_calls = 0
            run_start_ts = time.monotonic()

            async with SessionFactory() as session:
                offset = 0
                page_index = 0
                commits_since = 0
                batch_size = 5

                # 高价值帖子优先列表（从 post_scores_latest_v 挑核心帖）
                high_value_post_ids: Set[str] = set()
                try:
                    high_rows = await session.execute(
                        text(
                            """
                            SELECT ps.source_post_id
                            FROM post_scores_latest_v ps
                            WHERE ps.business_pool = 'core' OR ps.value_score >= 6
                            """
                        )
                    )
                    high_value_post_ids = {str(r[0]) for r in high_rows.fetchall() if r[0]}
                    logger.info(f"🎯 高价值帖子基数: {len(high_value_post_ids)}")
                except Exception as exc:
                    logger.warning(f"[WARN] 无法加载 post_scores_latest_v，评论回填将按原逻辑执行: {exc}")

                # 若无高价值帖子，跳过评论回填阶段
                if not high_value_post_ids:
                    logger.info("ℹ️ 无高价值帖子需要评论回填，已跳过评论阶段")
                    comments_summary = {
                        "processed_posts": 0,
                        "processed_comments": 0,
                    }
                else:
                    high_value_list = list(high_value_post_ids)

                    while True:
                        # 查询缺评论的帖子
                        stmt = text(
                            """
                            WITH curr AS (
                              SELECT DISTINCT ON (source_post_id, subreddit)
                                 source_post_id, subreddit, num_comments
                          FROM posts_raw
                          WHERE is_current = TRUE AND lower(subreddit) = ANY(:subs)
                            AND source_post_id = ANY(:post_ids)
                          ORDER BY source_post_id, subreddit
                        ), agg AS (
                          SELECT source_post_id, subreddit, COUNT(*) AS local_cnt
                          FROM comments
                          GROUP BY source_post_id, subreddit
                        )
                        SELECT c.source_post_id, c.subreddit
                        FROM curr c
                        LEFT JOIN agg a ON a.source_post_id=c.source_post_id AND a.subreddit=c.subreddit
                        WHERE c.num_comments > 0 AND COALESCE(a.local_cnt,0) < c.num_comments
                        ORDER BY c.subreddit, c.source_post_id
                        LIMIT :limit OFFSET :offset
                        """
                        )
                        params = {
                            "subs": [s.lower() for s in targets],
                            "post_ids": high_value_list,
                            "limit": args.comments_page_size,
                            "offset": offset,
                        }
                    
                    chunk = await session.execute(stmt, params)
                    rows = [(str(r[0]), str(r[1])) for r in chunk.fetchall()]
                    
                    if not rows:
                        if page_index == 0:
                            logger.info("✅ 所有帖子的评论已完成，无需回填")
                        break

                    page_index += 1
                    if page_index % 5 == 1:
                        logger.info(
                            f"[INFO] Page {page_index}: fetched {len(rows)} posts "
                            f"(offset={offset}), processed_posts={processed_posts}, "
                            f"processed_comments={processed_comments}"
                        )

                    # 分批处理（高价值优先：在同页内将核心帖排前）
                    def _sort_key(item: tuple[str, str]) -> tuple[int, str]:
                        pid, _sub = item
                        return (0 if pid in high_value_post_ids else 1, pid)

                    sorted_rows = sorted(rows, key=_sort_key)

                    for batch_start in range(0, len(sorted_rows), batch_size):
                        batch = sorted_rows[batch_start:batch_start + batch_size]
                        batch_index = batch_start // batch_size + 1

                        # 并发抓取评论
                        fetch_tasks = []
                        for pid, sub in batch:
                            fetch_tasks.append(
                                reddit_client.fetch_post_comments(
                                    pid, sort="confidence", depth=8,
                                    limit=args.comments_limit_per_post, mode="full"
                                )
                            )

                        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                        total_fetch_calls += len(batch)

                        # 串行写库
                        for (pid, sub), result in zip(batch, fetch_results):
                            if isinstance(result, Exception):
                                logger.warning(f"[WARN] Failed to fetch comments for post={pid}: {result}")
                                continue
                            if not result:
                                continue

                            try:
                                written = await persist_comments(
                                    session,
                                    source_post_id=pid,
                                    subreddit=sub,
                                    comments=result,
                                    source_track="backfill_comments",
                                    default_business_pool="lab",
                                )
                                processed_comments += written
                                processed_posts += 1
                                commits_since += 1
                                if commits_since >= 1:
                                    await session.commit()
                                    commits_since = 0
                            except Exception as exc:
                                logger.warning(f"[WARN] Failed to persist comments for post={pid}: {exc}")
                                try:
                                    await session.rollback()
                                except Exception:
                                    pass

                        # 软限流
                        if soft_rate_limit_per_min > 0 and total_fetch_calls > 0:
                            elapsed = time.monotonic() - run_start_ts
                            if elapsed > 0:
                                current_per_min = total_fetch_calls / (elapsed / 60.0)
                                if current_per_min > soft_rate_limit_per_min * 1.05:
                                    target_elapsed = total_fetch_calls * 60.0 / soft_rate_limit_per_min
                                    sleep_for = max(0.0, target_elapsed - elapsed)
                                    if sleep_for > 0:
                                        logger.info(
                                            f"[INFO] Soft rate-limit: {current_per_min:.2f}/min, sleeping {sleep_for:.1f}s"
                                        )
                                        await asyncio.sleep(sleep_for)

                    offset += len(rows)
                    
                    # 波浪式抓取：每页处理完后强制休息，避让反爬风控
                    logger.info("💤 Page done. Resting for 30s to avoid Reddit throttling...")
                    await asyncio.sleep(30)

                # 收尾提交
                await session.commit()

            logger.info(f"\n{'='*80}")
            logger.info("📊 评论回填完成！汇总统计：")
            logger.info(f"{'='*80}")
            logger.info(f"处理帖子数: {processed_posts}")
            logger.info(f"写入评论数: {processed_comments}")

            comments_summary = {
                "processed_posts": processed_posts,
                "processed_comments": processed_comments,
            }

        # ============================================================
        # 输出最终结果
        # ============================================================
        final_summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "comments_only" if args.comments_only else ("with_comments" if args.with_comments else "posts_only"),
            "posts": posts_summary,
            "comments": comments_summary,
        }

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(final_summary, f, indent=2, ensure_ascii=False)
            logger.info(f"📁 结果已保存到: {args.output}")
        else:
            print(json.dumps(final_summary, indent=2, ensure_ascii=False))

    finally:
        # 确保关闭 aiohttp session，避免 Unclosed client session 噪音
        try:
            await reddit_client.close()
        except Exception:
            logger.exception("Failed to close RedditAPIClient session")


if __name__ == "__main__":
    asyncio.run(main())
