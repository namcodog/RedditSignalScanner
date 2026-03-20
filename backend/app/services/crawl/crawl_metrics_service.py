from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.crawl_metrics import CrawlMetrics
from app.models.posts_storage import PostHot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CrawlMetricsInput:
    successful_crawls: int = 0
    empty_crawls: int = 0
    failed_crawls: int = 0
    total_new_posts: int = 0
    total_updated_posts: int = 0
    total_duplicates: int = 0
    avg_latency_seconds: float = 0.0


@dataclass(slots=True)
class CrawlMetricsDeps:
    db: AsyncSession
    now_factory: Callable[[], datetime] = field(
        default=lambda: datetime.now(timezone.utc)
    )


async def record_crawl_metrics(
    metrics_input: CrawlMetricsInput,
    deps: CrawlMetricsDeps,
) -> None:
    now = deps.now_factory()
    metric_date = now.date()
    metric_hour = now.hour

    result = await deps.db.execute(
        select(func.count(PostHot.source_post_id)).where(
            PostHot.cached_at >= now - timedelta(hours=24)
        )
    )
    valid_posts_24h = result.scalar() or 0

    result = await deps.db.execute(
        select(func.count(CommunityCache.community_name)).where(
            CommunityCache.is_active.is_(True)
        )
    )
    total_communities = result.scalar() or 0

    total_posts = (
        metrics_input.total_new_posts
        + metrics_input.total_updated_posts
        + metrics_input.total_duplicates
    )
    cache_hit_rate = (
        metrics_input.total_duplicates / total_posts * 100 if total_posts > 0 else 0.0
    )

    stmt = pg_insert(CrawlMetrics).values(
        metric_date=metric_date,
        metric_hour=metric_hour,
        cache_hit_rate=cache_hit_rate,
        valid_posts_24h=valid_posts_24h,
        total_communities=total_communities,
        successful_crawls=metrics_input.successful_crawls,
        empty_crawls=metrics_input.empty_crawls,
        failed_crawls=metrics_input.failed_crawls,
        avg_latency_seconds=metrics_input.avg_latency_seconds,
        total_new_posts=metrics_input.total_new_posts,
        total_updated_posts=metrics_input.total_updated_posts,
        total_duplicates=metrics_input.total_duplicates,
    )

    stmt = stmt.on_conflict_do_update(
        constraint="uq_crawl_metrics_date_hour",
        set_={
            "cache_hit_rate": cache_hit_rate,
            "valid_posts_24h": valid_posts_24h,
            "total_communities": total_communities,
            "successful_crawls": CrawlMetrics.successful_crawls
            + metrics_input.successful_crawls,
            "empty_crawls": CrawlMetrics.empty_crawls + metrics_input.empty_crawls,
            "failed_crawls": CrawlMetrics.failed_crawls + metrics_input.failed_crawls,
            "avg_latency_seconds": metrics_input.avg_latency_seconds,
            "total_new_posts": CrawlMetrics.total_new_posts
            + metrics_input.total_new_posts,
            "total_updated_posts": CrawlMetrics.total_updated_posts
            + metrics_input.total_updated_posts,
            "total_duplicates": CrawlMetrics.total_duplicates
            + metrics_input.total_duplicates,
        },
    )

    await deps.db.execute(stmt)
    await deps.db.commit()

    logger.info(
        "📊 埋点记录: %s %s:00 - 成功=%s, 空结果=%s, 失败=%s, 新增=%s, 更新=%s, 去重=%s",
        metric_date,
        metric_hour,
        metrics_input.successful_crawls,
        metrics_input.empty_crawls,
        metrics_input.failed_crawls,
        metrics_input.total_new_posts,
        metrics_input.total_updated_posts,
        metrics_input.total_duplicates,
    )


__all__ = [
    "CrawlMetricsDeps",
    "CrawlMetricsInput",
    "record_crawl_metrics",
]
