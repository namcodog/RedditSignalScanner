from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable, Mapping

from app.core.config import Settings
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    compute_idempotency_key,
    compute_idempotency_key_human,
)

DEFAULT_HIGH_VALUE_SUBREDDITS = [
    "AmazonWFShoppers",
    "FacebookAds",
    "EtsySellers",
    "Aliexpress",
    "AmazonFlexDrivers",
    "bigseo",
    "dropshipping",
    "amazonecho",
    "Legomarket",
    "dropship",
    "FulfillmentByAmazon",
    "amazonprime",
    "FASCAmazon",
    "peopleofwalmart",
    "AliExpressBR",
    "Etsy",
    "stickerstore",
    "digital_marketing",
    "amazon",
    "AmazonMerch",
    "Amazon_Influencer",
    "logistics",
    "AmazonSeller",
    "TikTokshop",
    "BestAliExpressFinds",
    "TechSEO",
    "AmazonFBA",
    "AmazonFBAOnlineRetail",
    "News_Walmart",
    "printondemand",
    "walmart_RX",
    "amazonemployees",
    "WalmartSellers",
    "WalmartCanada",
    "AmazonFBATips",
    "ecommercemarketing",
    "Dropshipping_Guide",
    "SpellcasterReviews",
    "AmazonWTF",
    "ShopifyeCommerce",
    "shopifyDev",
    "MerchByAmazon",
    "amazonfresh",
    "DropshippingTips",
    "AntiAmazon",
    "ShopifyAppDev",
    "AmazonAnswers",
    "fuckamazon",
]


def normalize_configured_subreddits(raw: str) -> list[str]:
    return [item.strip().replace("r/", "") for item in raw.split(",") if item.strip()]


def select_time_filter(lookback_days: int) -> str:
    if lookback_days <= 1:
        return "day"
    if lookback_days <= 7:
        return "week"
    if lookback_days <= 30:
        return "month"
    return "all"


def build_reddit_client_kwargs(settings: Settings) -> dict[str, Any]:
    return {
        "client_id": settings.reddit_client_id,
        "client_secret": settings.reddit_client_secret,
        "user_agent": settings.reddit_user_agent,
        "rate_limit": settings.reddit_rate_limit,
        "rate_limit_window": settings.reddit_rate_limit_window_seconds,
        "request_timeout": settings.reddit_request_timeout_seconds,
        "max_concurrency": settings.reddit_max_concurrency,
    }


def build_backfill_comments_plan(
    *,
    source_post_id: str,
    subreddit: str,
    reason: str,
    limit: int,
    mode: str,
    depth: int,
    label_after_ingest: bool = False,
    extra_meta: Mapping[str, Any] | None = None,
) -> CrawlPlanContract:
    meta: dict[str, Any] = {
        "subreddit": subreddit,
        "mode": mode,
        "depth": int(depth),
        "sort": "confidence",
    }
    if mode == "smart_shallow":
        meta.update(
            {
                "smart_top_limit": 30,
                "smart_new_limit": 20,
                "smart_reply_top_limit": 15,
                "smart_reply_per_top": 1,
                "smart_total_limit": int(limit),
                "smart_top_sort": "top",
                "smart_new_sort": "new",
            }
        )
    if label_after_ingest:
        meta["label_after_ingest"] = True
    if extra_meta:
        meta.update(dict(extra_meta))
    return CrawlPlanContract(
        plan_kind="backfill_comments",
        target_type="post_ids",
        target_value=str(source_post_id),
        reason=reason,
        limits=CrawlPlanLimits(comments_limit=int(limit)),
        meta=meta,
    )


async def enqueue_backfill_comments_target(
    *,
    session: Any,
    crawl_run_id: str,
    subreddit: str,
    plan: CrawlPlanContract,
    queue: str,
    ensure_crawler_run_target: Callable[..., Awaitable[Any]],
    enqueue_execute_target_outbox: Callable[..., Awaitable[Any]],
) -> str:
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
        queue=queue,
    )
    return target_id


__all__ = [
    "DEFAULT_HIGH_VALUE_SUBREDDITS",
    "build_backfill_comments_plan",
    "build_reddit_client_kwargs",
    "enqueue_backfill_comments_target",
    "normalize_configured_subreddits",
    "select_time_filter",
]
