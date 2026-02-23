"""Generate warmup period report (JSON + human-readable summary).

Usage:
    python scripts/generate_warmup_report.py

Output:
    ../reports/warmup-report.json (relative to backend directory)
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Ensure backend package importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.models.beta_feedback import BetaFeedback
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.task import Task
from app.models.user import User
from app.tasks.monitoring_task import monitor_warmup_metrics


async def _gather_from_db() -> Dict[str, Any]:
    """Aggregate DB-backed metrics for the report."""
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        # Community pool
        seed_count = (await session.execute(select(func.count(CommunityPool.id)))).scalar_one()
        discovered_count = (await session.execute(select(func.count(DiscoveredCommunity.id)))).scalar_one()
        # Cache metrics
        total_posts_cached = (await session.execute(select(func.coalesce(func.sum(CommunityCache.posts_cached), 0)))).scalar_one()
        rows = (await session.execute(select(CommunityCache.last_crawled_at))).scalars().all()
        if rows:
            total_age_hours = sum(((now - ts).total_seconds() / 3600.0) for ts in rows)
            avg_cache_age_hours = total_age_hours / len(rows)
        else:
            avg_cache_age_hours = 0.0
        # User testing
        total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
        beta_users = (await session.execute(select(func.count(func.distinct(BetaFeedback.user_id))))).scalar_one()
        internal_users = max(total_users - beta_users, 0)
        total_analyses = (await session.execute(select(func.count(Task.id)))).scalar_one()
        avg_satisfaction = (await session.execute(select(func.coalesce(func.avg(BetaFeedback.satisfaction), 0.0)))).scalar_one()
        # System performance (task durations)
        durations = []  # seconds
        result = await session.execute(select(Task.started_at, Task.completed_at))
        for started_at, completed_at in result.all():
            if started_at and completed_at:
                durations.append((completed_at - started_at).total_seconds())
        if durations:
            durations.sort()
            avg_analysis_time = sum(durations) / len(durations)
            p95_index = int(0.95 * (len(durations) - 1))
            p95_analysis_time = durations[p95_index]
        else:
            avg_analysis_time = 0.0
            p95_analysis_time = 0.0
    return {
        "community_pool": {
            "seed_communities": int(seed_count),
            "discovered_communities": int(discovered_count),
            "total": int(seed_count + discovered_count),
        },
        "cache_metrics": {
            "total_posts_cached": int(total_posts_cached),
            "avg_cache_age_hours": float(avg_cache_age_hours),
        },
        "user_testing": {
            "internal_users": int(internal_users),
            "beta_users": int(beta_users),
            "total_analyses": int(total_analyses),
            "avg_satisfaction": float(avg_satisfaction),
        },
        "system_performance": {
            "avg_analysis_time_seconds": float(avg_analysis_time),
            "p95_analysis_time_seconds": float(p95_analysis_time),
            "uptime_percentage": 100.0,
        },
    }


async def build_report_async(precomputed_metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Async builder for the warmup report payload.

    Note: to avoid nested event-loop issues, real-time metrics should be computed
    outside of the event loop and passed in via `precomputed_metrics`.
    """
    metrics: Dict[str, Any] = precomputed_metrics or {}
    adaptive_hours = celery_app.conf.get("adaptive_crawl_hours")

    db_part = await _gather_from_db()

    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warmup_period": "Day 13-19 (7 days)",
        "adaptive_crawl_hours": adaptive_hours,
        "community_pool": db_part["community_pool"],
        "cache_metrics": {
            **db_part["cache_metrics"],
            "cache_hit_rate": float(metrics.get("cache_hit_rate", 0.0)),
        },
        "api_usage": {
            "total_calls": 0,
            "avg_calls_per_minute": int(metrics.get("api_calls_per_minute", 0)),
            "peak_calls_per_minute": int(metrics.get("api_calls_per_minute", 0)),
        },
        "user_testing": db_part["user_testing"],
        "system_performance": db_part["system_performance"],
    }
    return payload


def build_report() -> Dict[str, Any]:
    """Synchronous builder used by CLI: compute real-time metrics first, then run async DB aggregation."""
    realtime_metrics = monitor_warmup_metrics()
    return asyncio.run(build_report_async(precomputed_metrics=realtime_metrics))


def main() -> int:
    payload = build_report()

    reports_dir = BACKEND_DIR.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "warmup-report.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Human-readable summary
    print("Warmup Report Summary")
    print("- generated_at:", payload["generated_at"])
    print("- warmup_period:", payload["warmup_period"])
    print("- community_pool_total:", payload["community_pool"]["total"])
    print("- cache_hit_rate:", payload["cache_metrics"].get("cache_hit_rate"))
    print("- avg_cache_age_hours:", payload["cache_metrics"].get("avg_cache_age_hours"))
    print("- api_calls_per_minute(avg):", payload["api_usage"]["avg_calls_per_minute"])
    print(f"\nSaved to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
