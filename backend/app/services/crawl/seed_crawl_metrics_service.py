from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.crawl_metrics import CrawlMetrics
from app.services.infrastructure.tiered_scheduler import TieredScheduler

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SeedCrawlMetricsInput:
    results: list[dict[str, Any]]
    total_profiles: int


@dataclass(slots=True)
class SeedCrawlMetricsDeps:
    session_factory: Callable[[], Any]
    scheduler_factory: Callable[[Any], Any]
    crawl_metrics_model: Any
    build_upsert_stmt: Callable[..., Any]
    now_factory: Callable[[], datetime]


@dataclass(slots=True)
class SeedCrawlMetricsResult:
    success_count: int
    failure_count: int
    empty_count: int
    total_new: int
    avg_latency: float
    tier_metrics_payload: dict[str, Any]


def _default_build_upsert_stmt(
    *,
    model: Any,
    metric_date: Any,
    metric_hour: int,
    cache_hit_rate: float,
    valid_posts_24h: int,
    total_communities: int,
    successful_crawls: int,
    empty_crawls: int,
    failed_crawls: int,
    avg_latency_seconds: float,
    total_new_posts: int,
    total_updated_posts: int,
    total_duplicates: int,
    tier_assignments: dict[str, Any],
) -> Any:
    stmt = pg_insert(model).values(
        metric_date=metric_date,
        metric_hour=metric_hour,
        cache_hit_rate=cache_hit_rate,
        valid_posts_24h=valid_posts_24h,
        total_communities=total_communities,
        successful_crawls=successful_crawls,
        empty_crawls=empty_crawls,
        failed_crawls=failed_crawls,
        avg_latency_seconds=avg_latency_seconds,
        total_new_posts=total_new_posts,
        total_updated_posts=total_updated_posts,
        total_duplicates=total_duplicates,
        tier_assignments=tier_assignments,
    )
    return stmt.on_conflict_do_update(
        constraint="uq_crawl_metrics_date_hour",
        set_={
            "cache_hit_rate": stmt.excluded.cache_hit_rate,
            "valid_posts_24h": stmt.excluded.valid_posts_24h,
            "total_communities": stmt.excluded.total_communities,
            "successful_crawls": model.successful_crawls + successful_crawls,
            "empty_crawls": model.empty_crawls + empty_crawls,
            "failed_crawls": model.failed_crawls + failed_crawls,
            "avg_latency_seconds": stmt.excluded.avg_latency_seconds,
            "total_new_posts": model.total_new_posts + total_new_posts,
            "total_updated_posts": model.total_updated_posts + total_updated_posts,
            "total_duplicates": model.total_duplicates + total_duplicates,
            "tier_assignments": stmt.excluded.tier_assignments,
        },
    )


async def record_seed_crawl_metrics(
    *,
    metrics_input: SeedCrawlMetricsInput,
    deps: SeedCrawlMetricsDeps,
) -> SeedCrawlMetricsResult:
    results = metrics_input.results
    success_count = sum(1 for item in results if item.get("status") == "success")
    failure_count = len(results) - success_count
    rate_limit_hits = sum(1 for item in results if item.get("rate_limited"))
    downgraded = [item.get("community") for item in results if item.get("rate_limited")]
    total_new = sum(r.get("posts_count", 0) for r in results if r.get("status") == "success")
    duration_values = [
        float(r.get("duration_seconds", 0))
        for r in results
        if isinstance(r.get("duration_seconds"), (int, float))
    ]
    avg_latency = sum(duration_values) / len(duration_values) if duration_values else 0.0
    empty_count = sum(
        1
        for r in results
        if r.get("status") == "success" and r.get("posts_count", 0) == 0
    )

    tier_assignments: dict[str, Any] | None = None
    tier_metrics_payload: dict[str, Any] = {
        "assignments": {},
        "rate_limit_hits": rate_limit_hits,
        "downgraded_communities": [c for c in downgraded if c],
    }

    async with deps.session_factory() as metrics_db:
        try:
            scheduler = deps.scheduler_factory(metrics_db)
            tier_assignments = await scheduler.calculate_assignments()
            await scheduler.apply_assignments(tier_assignments)
        except Exception:
            logger.exception("刷新 quality_tier 失败")

        tier_metrics_payload["assignments"] = tier_assignments or {}

        try:
            now = deps.now_factory()
            cache_hit_rate = (success_count / max(1, metrics_input.total_profiles)) * 100.0
            logger.info(
                "准备写入 crawl_metrics: total=%s, success=%s, empty=%s, failed=%s",
                metrics_input.total_profiles,
                success_count,
                empty_count,
                failure_count,
            )

            used_upsert = False
            try:
                model = deps.crawl_metrics_model
                if hasattr(model, "__table__") or hasattr(model, "__mapper__"):
                    stmt = deps.build_upsert_stmt(
                        model=model,
                        metric_date=now.date(),
                        metric_hour=now.hour,
                        cache_hit_rate=cache_hit_rate,
                        valid_posts_24h=total_new,
                        total_communities=metrics_input.total_profiles,
                        successful_crawls=success_count,
                        empty_crawls=empty_count,
                        failed_crawls=failure_count,
                        avg_latency_seconds=avg_latency,
                        total_new_posts=total_new,
                        total_updated_posts=0,
                        total_duplicates=0,
                        tier_assignments=tier_metrics_payload,
                    )
                    await metrics_db.execute(stmt)
                    await metrics_db.commit()
                    used_upsert = True
                    logger.info("✅ crawl_metrics upsert 成功")
            except Exception as exc:
                logger.warning("crawl_metrics upsert 失败，回退到 add()：%s", exc)

            if not used_upsert:
                metrics_obj = deps.crawl_metrics_model(
                    metric_date=now.date(),
                    metric_hour=now.hour,
                    cache_hit_rate=cache_hit_rate,
                    valid_posts_24h=total_new,
                    total_communities=metrics_input.total_profiles,
                    successful_crawls=success_count,
                    empty_crawls=empty_count,
                    failed_crawls=failure_count,
                    avg_latency_seconds=avg_latency,
                    total_new_posts=total_new,
                    total_updated_posts=0,
                    total_duplicates=0,
                    tier_assignments=tier_metrics_payload,
                )
                metrics_db.add(metrics_obj)
                await metrics_db.commit()
                logger.info("✅ crawl_metrics 持久化成功（fallback add()）")
        except Exception:
            logger.exception("写入 crawl_metrics 失败")
            try:
                await metrics_db.rollback()
            except Exception:
                logger.exception("回滚 crawl_metrics 事务失败")

    return SeedCrawlMetricsResult(
        success_count=success_count,
        failure_count=failure_count,
        empty_count=empty_count,
        total_new=total_new,
        avg_latency=avg_latency,
        tier_metrics_payload=tier_metrics_payload,
    )


def build_default_seed_crawl_metrics_deps() -> SeedCrawlMetricsDeps:
    from app.db.session import SessionFactory

    return SeedCrawlMetricsDeps(
        session_factory=SessionFactory,
        scheduler_factory=TieredScheduler,
        crawl_metrics_model=CrawlMetrics,
        build_upsert_stmt=_default_build_upsert_stmt,
        now_factory=lambda: datetime.now(timezone.utc),
    )


__all__ = [
    "SeedCrawlMetricsDeps",
    "SeedCrawlMetricsInput",
    "SeedCrawlMetricsResult",
    "build_default_seed_crawl_metrics_deps",
    "record_seed_crawl_metrics",
]
