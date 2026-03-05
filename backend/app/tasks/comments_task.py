from __future__ import annotations

from typing import Any, Iterable, Mapping
import os
import uuid
from sqlalchemy import text

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.services.crawl.comments_ingest import persist_comments
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.core.config import get_settings
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.services.labeling.labeling_service import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.services.infrastructure.subreddit_snapshot import persist_subreddit_snapshot
from app.services.labeling.labeling_posts import label_posts_recent
from app.services.infrastructure.moderation_metrics import compute_removal_ratio_by_subreddit, to_rules_friendliness_score
from app.utils.asyncio_runner import run as run_coro

logger = get_task_logger(__name__)
COMMENTS_BACKFILL_QUEUE = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")

@celery_app.task(name="comments.ingest_post_comments")
def ingest_post_comments(
    *,
    source_post_id: str,
    subreddit: str,
    comments: Iterable[Mapping[str, Any]],
    source: str = "reddit",
) -> dict[str, int | str]:
    """Persist comments for a single post. Idempotent by reddit_comment_id.

    This task intentionally avoids network calls; upstream should supply comment payloads.
    """
    items = list(comments)
    crawl_run_id = str(uuid.uuid4())
    logger.info(
        "Ingesting %s comments for post=%s in %s (crawl_run_id=%s)",
        len(items),
        source_post_id,
        subreddit,
        crawl_run_id,
    )
    async def _run() -> int:
        async with SessionFactory() as session:
            return await persist_comments(
                session,
                source_post_id=source_post_id,
                subreddit=subreddit,
                comments=items,
                source=source,
                source_track="incremental_preview",
                default_business_pool="lab",
                crawl_run_id=crawl_run_id,
            )

    processed = run_coro(_run())
    return {"processed": processed, "status": "ok"}


@celery_app.task(name="comments.fetch_and_ingest")
def fetch_and_ingest_post_comments(
    *,
    source_post_id: str,
    subreddit: str,
    mode: str = "smart_shallow",
    limit: int = 50,
    depth: int = 2,
) -> dict[str, int | str]:
    """
    收口版：不再在 comments_task 里直抓直写库。

    只做：生成 backfill_comments plan（crawler_run_targets）+ enqueue 到统一执行入口 execute_target。
    """

    async def _run() -> dict[str, Any]:
        crawl_run_id = str(uuid.uuid4())
        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=str(source_post_id),
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=int(limit)),
            meta={
                "subreddit": subreddit,
                "mode": mode,
                "depth": int(depth),
                "sort": "confidence",
                "smart_top_limit": 30,
                "smart_new_limit": 20,
                "smart_reply_top_limit": 15,
                "smart_reply_per_top": 1,
                "smart_total_limit": int(limit),
                "smart_top_sort": "top",
                "smart_new_sort": "new",
            },
        )
        idempotency_key = compute_idempotency_key(plan)
        idempotency_key_human = compute_idempotency_key_human(plan)
        target_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}"
            )
        )

        async with SessionFactory() as session:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={
                    "mode": "manual_backfill_comments",
                    "source": "comments_task",
                    "subreddit": subreddit,
                    "post_id": source_post_id,
                },
            )
            await ensure_crawler_run_target(
                session,
                community_run_id=target_id,
                crawl_run_id=crawl_run_id,
                subreddit=subreddit,
                status="queued",
                plan_kind=plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                config=plan.model_dump(mode="json"),
            )
            await enqueue_execute_target_outbox(
                session,
                target_id=target_id,
                queue=COMMENTS_BACKFILL_QUEUE,
            )
            await session.commit()
        return {"enqueued": 1, "target_id": target_id, "crawl_run_id": crawl_run_id}

    result = run_coro(_run())
    return {"status": "ok", **result}


@celery_app.task(name="comments.label_comments")
def label_comments_task(*, reddit_comment_ids: list[str]) -> dict[str, int | str]:
    async def _run() -> dict[str, int]:
        async with SessionFactory() as session:
            n1 = await classify_and_label_comments(session, reddit_comment_ids)
            n2 = await extract_and_label_entities_for_comments(
                session, reddit_comment_ids
            )
            await session.commit()
            return {"labeled": n1, "entities": n2}

    result = run_coro(_run())
    return {"status": "ok", **result}


@celery_app.task(name="comments.backfill_full")
def backfill_full_comments(
    *,
    source_post_ids: list[str],
    subreddit: str,
    limit: int = 500,
) -> dict[str, int | str]:
    """Backfill full comment trees for given posts and label them.

    This is a P1 batch task intended for off-peak windows.
    """
    # 收口版：只生成 plan + enqueue，执行与写库统一走 execute_target

    async def _run() -> dict[str, Any]:
        crawl_run_id = str(uuid.uuid4())
        target_ids: list[str] = []

        async with SessionFactory() as session:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={
                    "mode": "backfill_full_comments",
                    "source": "comments_task",
                    "subreddit": subreddit,
                    "posts": len(source_post_ids),
                    "limit": int(limit),
                },
            )

            for pid in source_post_ids:
                plan = CrawlPlanContract(
                    plan_kind="backfill_comments",
                    target_type="post_ids",
                    target_value=str(pid),
                    reason="backfill_full_comments",
                    limits=CrawlPlanLimits(comments_limit=int(limit)),
                    meta={
                        "subreddit": subreddit,
                        "mode": "full",
                        "depth": 8,
                        "sort": "confidence",
                        "label_after_ingest": True,
                    },
                )
                idempotency_key = compute_idempotency_key(plan)
                idempotency_key_human = compute_idempotency_key_human(plan)
                target_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                    )
                )
                await ensure_crawler_run_target(
                    session,
                    community_run_id=target_id,
                    crawl_run_id=crawl_run_id,
                    subreddit=subreddit,
                    status="queued",
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    config=plan.model_dump(mode="json"),
                )
                await enqueue_execute_target_outbox(
                    session,
                    target_id=target_id,
                    queue=COMMENTS_BACKFILL_QUEUE,
                )
                target_ids.append(target_id)

            await session.commit()

        return {"enqueued": len(target_ids), "crawl_run_id": crawl_run_id}

    result = run_coro(_run())
    return {"status": "ok", **result}


@celery_app.task(name="comments.backfill_recent_full_daily")
def backfill_recent_full_daily() -> dict[str, int | str]:
    """Nightly backfill of recent posts' full comments for configured subreddits.

    Environment variables:
      - COMMENTS_BACKFILL_SUBS: comma-separated subreddits (e.g., r/homegym,r/Fitness)
      - COMMENTS_BACKFILL_DAYS: lookback window in days (default 7)
      - COMMENTS_BACKFILL_POST_LIMIT: posts per subreddit (default 20)
    """
    import os

    settings = get_settings()
    subs_raw = os.getenv("COMMENTS_BACKFILL_SUBS", "").strip()
    lookback_days = int(os.getenv("COMMENTS_BACKFILL_DAYS", "7"))
    per_sub_limit = int(os.getenv("COMMENTS_BACKFILL_POST_LIMIT", "20"))
    subreddits = [s.strip().replace("r/", "") for s in subs_raw.split(",") if s.strip()]

    async def _run() -> dict[str, int]:
        crawl_run_id = str(uuid.uuid4())
        target_ids: list[str] = []
        if not subreddits:
            return {"processed": 0, "labeled": 0}
        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            rate_limit=settings.reddit_rate_limit,
            rate_limit_window=settings.reddit_rate_limit_window_seconds,
            request_timeout=settings.reddit_request_timeout_seconds,
            max_concurrency=settings.reddit_max_concurrency,
        ) as reddit:
            async with SessionFactory() as session:
                await ensure_crawler_run(
                    session,
                    crawl_run_id=crawl_run_id,
                    config={
                        "mode": "backfill_recent_full_daily",
                        "source": "comments_task",
                        "subreddits": subreddits,
                        "lookback_days": lookback_days,
                        "per_sub_limit": per_sub_limit,
                    },
                )
                for sub in subreddits:
                    try:
                        posts = await reddit.fetch_subreddit_posts(
                            sub,
                            limit=per_sub_limit,
                            time_filter="week" if lookback_days > 1 else "day",
                            sort="top",
                        )
                    except Exception:
                        continue
                    for p in posts:
                        try:
                            plan = CrawlPlanContract(
                                plan_kind="backfill_comments",
                                target_type="post_ids",
                                target_value=str(p.id),
                                reason="backfill_recent_full_daily",
                                limits=CrawlPlanLimits(comments_limit=500),
                                meta={
                                    "subreddit": f"r/{sub}",
                                    "mode": "full",
                                    "depth": 8,
                                    "sort": "confidence",
                                    "label_after_ingest": True,
                                },
                            )
                            idempotency_key = compute_idempotency_key(plan)
                            idempotency_key_human = compute_idempotency_key_human(plan)
                            target_id = str(
                                uuid.uuid5(
                                    uuid.NAMESPACE_URL,
                                    f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                                )
                            )
                            await ensure_crawler_run_target(
                                session,
                                community_run_id=target_id,
                                crawl_run_id=crawl_run_id,
                                subreddit=f"r/{sub}",
                                status="queued",
                                plan_kind=plan.plan_kind,
                                idempotency_key=idempotency_key,
                                idempotency_key_human=idempotency_key_human,
                                config=plan.model_dump(mode="json"),
                            )
                            await enqueue_execute_target_outbox(
                                session,
                                target_id=target_id,
                                queue=COMMENTS_BACKFILL_QUEUE,
                            )
                            target_ids.append(target_id)
                        except Exception:
                            # 出现异常时回滚，清理当前事务
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                            continue
                await session.commit()

        return {"processed": 0, "labeled": 0, "enqueued": len(target_ids), "crawl_run_id": crawl_run_id}

    import asyncio

    return {"status": "ok", **run_coro(_run())}


@celery_app.task(name="subreddit.capture_snapshot_daily")
def capture_snapshot_daily() -> dict[str, int | str]:
    """Nightly snapshot of configured subreddits' about/rules.

    Environment:
      - COMMENTS_BACKFILL_SUBS: comma-separated subreddits
    """
    import os
    settings = get_settings()
    subs_raw = os.getenv("COMMENTS_BACKFILL_SUBS", "").strip()
    subreddits = [s.strip().replace("r/", "") for s in subs_raw.split(",") if s.strip()]

    async def _run() -> int:
        if not subreddits:
            return 0
        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            rate_limit=settings.reddit_rate_limit,
            rate_limit_window=settings.reddit_rate_limit_window_seconds,
            request_timeout=settings.reddit_request_timeout_seconds,
            max_concurrency=settings.reddit_max_concurrency,
        ) as reddit:
            async with SessionFactory() as session:
                count = 0
                for sub in subreddits:
                    try:
                        about = await reddit.fetch_subreddit_about(sub)
                        rules = await reddit.fetch_subreddit_rules(sub)
                        # compute moderation score from recent removal ratio
                        ratios = await compute_removal_ratio_by_subreddit(session, since_days=30, subreddits=[sub])
                        modscore = to_rules_friendliness_score(ratios.get(sub.lower(), 0.0))
                        await persist_subreddit_snapshot(
                            session,
                            subreddit=sub,
                            subscribers=about.get("subscribers"),
                            active_user_count=about.get("active_user_count"),
                            rules_text=rules,
                            over18=about.get("over18"),
                        )
                        # update moderation_score for the last inserted row for this subreddit
                        await session.execute(
                            text(
                                """
                                UPDATE subreddit_snapshots SET moderation_score=:score
                                WHERE id = (
                                  SELECT id FROM subreddit_snapshots
                                  WHERE subreddit=:sub ORDER BY captured_at DESC LIMIT 1
                                )
                                """
                            ),
                            {"score": int(modscore), "sub": sub},
                        )
                        count += 1
                    except Exception:
                        continue
                await session.commit()
                return count

    import asyncio

    return {"status": "ok", "snapshots": run_coro(_run())}


@celery_app.task(name="posts.label_recent")
def label_posts_recent_task() -> dict[str, int | str]:
    """Daily labeling for recent posts (posts_hot) to unify content_labels/entities for posts.

    Env:
      - POSTS_LABEL_DAYS (default 7)
      - POSTS_LABEL_LIMIT (default 500)
    """
    import os
    days = int(os.getenv("POSTS_LABEL_DAYS", "7"))
    limit = int(os.getenv("POSTS_LABEL_LIMIT", "500"))

    async def _run() -> dict[str, int]:
        async with SessionFactory() as session:
            out = await label_posts_recent(session, since_days=days, limit=limit)
            await session.commit()
            return out

    result = run_coro(_run())
    return {"status": "ok", **result}


@celery_app.task(name="comments.backfill_high_value_full")
def backfill_high_value_comments() -> dict[str, int | str]:
    """批量抓取48个高价值社区的全量评论（深度8层，最多500条/帖）

    高价值社区列表（48个）：
    r/AmazonWFShoppers, r/FacebookAds, r/EtsySellers, r/Aliexpress, r/AmazonFlexDrivers,
    r/bigseo, r/dropshipping, r/amazonecho, r/Legomarket, r/dropship, r/FulfillmentByAmazon,
    r/amazonprime, r/FASCAmazon, r/peopleofwalmart, r/AliExpressBR, r/Etsy, r/stickerstore,
    r/digital_marketing, r/amazon, r/AmazonMerch, r/Amazon_Influencer, r/logistics,
    r/AmazonSeller, r/TikTokshop, r/BestAliExpressFinds, r/TechSEO, r/AmazonFBA,
    r/AmazonFBAOnlineRetail, r/News_Walmart, r/printondemand, r/walmart_RX, r/amazonemployees,
    r/WalmartSellers, r/WalmartCanada, r/AmazonFBATips, r/ecommercemarketing,
    r/Dropshipping_Guide, r/SpellcasterReviews, r/AmazonWTF, r/ShopifyeCommerce,
    r/shopifyDev, r/MerchByAmazon, r/amazonfresh, r/DropshippingTips, r/AntiAmazon,
    r/ShopifyAppDev, r/AmazonAnswers, r/fuckamazon

    Environment variables:
      - HIGH_VALUE_COMMENTS_POST_LIMIT: posts per subreddit (default 50)
      - HIGH_VALUE_COMMENTS_LOOKBACK_DAYS: lookback window in days (default 30)
    """
    import os
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()

    # 48个高价值社区列表
    HIGH_VALUE_SUBREDDITS = [
        "AmazonWFShoppers", "FacebookAds", "EtsySellers", "Aliexpress", "AmazonFlexDrivers",
        "bigseo", "dropshipping", "amazonecho", "Legomarket", "dropship", "FulfillmentByAmazon",
        "amazonprime", "FASCAmazon", "peopleofwalmart", "AliExpressBR", "Etsy", "stickerstore",
        "digital_marketing", "amazon", "AmazonMerch", "Amazon_Influencer", "logistics",
        "AmazonSeller", "TikTokshop", "BestAliExpressFinds", "TechSEO", "AmazonFBA",
        "AmazonFBAOnlineRetail", "News_Walmart", "printondemand", "walmart_RX", "amazonemployees",
        "WalmartSellers", "WalmartCanada", "AmazonFBATips", "ecommercemarketing",
        "Dropshipping_Guide", "SpellcasterReviews", "AmazonWTF", "ShopifyeCommerce",
        "shopifyDev", "MerchByAmazon", "amazonfresh", "DropshippingTips", "AntiAmazon",
        "ShopifyAppDev", "AmazonAnswers", "fuckamazon"
    ]

    per_sub_limit = int(os.getenv("HIGH_VALUE_COMMENTS_POST_LIMIT", "50"))
    lookback_days = int(os.getenv("HIGH_VALUE_COMMENTS_LOOKBACK_DAYS", "30"))

    async def _run() -> dict[str, int]:
        crawl_run_id = str(uuid.uuid4())
        total_processed = 0
        total_labeled = 0
        total_posts = 0
        failed_subs = []

        logger.info(f"🎯 开始抓取48个高价值社区的全量评论（每社区{per_sub_limit}个帖子，回溯{lookback_days}天）")

        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            rate_limit=settings.reddit_rate_limit,
            rate_limit_window=settings.reddit_rate_limit_window_seconds,
            request_timeout=settings.reddit_request_timeout_seconds,
            max_concurrency=settings.reddit_max_concurrency,
        ) as reddit:
            async with SessionFactory() as session:
                for sub in HIGH_VALUE_SUBREDDITS:
                    try:
                        logger.info("📥 正在抓取 r/%s 的帖子...", sub)
                        # 根据回溯天数选择时间过滤器
                        if lookback_days <= 1:
                            time_filter = "day"
                        elif lookback_days <= 7:
                            time_filter = "week"
                        elif lookback_days <= 30:
                            time_filter = "month"
                        else:
                            time_filter = "all"

                        posts = await reddit.fetch_subreddit_posts(
                            sub, limit=per_sub_limit, time_filter=time_filter, sort="top"
                        )
                        total_posts += len(posts)
                        logger.info("✅ r/%s: 获取到 %d 个帖子", sub, len(posts))

                        for p in posts:
                            try:
                                # 🔥 全量评论抓取：depth=8, limit=500, mode="full"
                                items = await reddit.fetch_post_comments(
                                    p.id, sort="confidence", depth=8, limit=500, mode="full"
                                )
                                if not items:
                                    continue

                                await persist_comments(
                                    session,
                                    source_post_id=p.id,
                                    subreddit=sub,
                                    comments=items,
                                    crawl_run_id=crawl_run_id,
                                )

                                # 评论语义标注
                                ids = [c.get("id") for c in items if c.get("id")]
                                total_labeled += await classify_and_label_comments(session, ids)
                                total_labeled += await extract_and_label_entities_for_comments(session, ids)
                                total_processed += len(items)

                                logger.debug("  ✓ 帖子 %s: %d 条评论", p.id, len(items))
                                # 每个帖子成功后提交一次，避免单个社区内长事务持锁
                                await session.commit()
                            except Exception as e:
                                # 捕获异常后回滚当前事务，清理锁与连接状态
                                try:
                                    await session.rollback()
                                except Exception:
                                    pass
                                logger.warning("  ✗ 帖子 %s 评论抓取失败: %s", p.id, e)
                                continue

                        logger.info("✅ r/%s 完成: 共处理 %d 个帖子", sub, len(posts))
                    except Exception as e:
                        logger.error("❌ r/%s 抓取失败: %s", sub, e)
                        failed_subs.append(sub)
                        continue

        logger.info(
            f"🎉 高价值社区评论抓取完成: "
            f"社区数={len(HIGH_VALUE_SUBREDDITS)}, 帖子数={total_posts}, "
            f"评论数={total_processed}, 标注数={total_labeled}, 失败数={len(failed_subs)}"
        )

        return {
            "processed": total_processed,
            "labeled": total_labeled,
            "total_posts": total_posts,
            "total_subreddits": len(HIGH_VALUE_SUBREDDITS),
            "failed_subreddits": failed_subs,
        }

    import asyncio
    result = run_coro(_run())
    return {"status": "ok", **result}
