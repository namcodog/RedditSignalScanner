from __future__ import annotations

"""
DB helper: fetch latest crawl_metrics record (by metric_date, metric_hour).

Outputs JSON to stdout and writes snapshot under reports/local-acceptance/.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import Select, select, desc

from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics


async def main() -> int:
    async with SessionFactory() as s:
        stmt: Select[Any] = (
            select(CrawlMetrics)
            .order_by(desc(CrawlMetrics.metric_date), desc(CrawlMetrics.metric_hour))
            .limit(1)
        )
        row = (await s.execute(stmt)).scalar_one_or_none()
        if row is None:
            payload = {"error": "no_metrics"}
        else:
            payload = {
                "metric_date": row.metric_date.isoformat(),
                "metric_hour": int(row.metric_hour),
                "cache_hit_rate": float(row.cache_hit_rate),
                "valid_posts_24h": int(row.valid_posts_24h),
                "total_communities": int(row.total_communities),
                "successful_crawls": int(row.successful_crawls),
                "empty_crawls": int(row.empty_crawls),
                "failed_crawls": int(row.failed_crawls),
                "avg_latency_seconds": float(row.avg_latency_seconds),
                "total_new_posts": int(row.total_new_posts),
                "total_updated_posts": int(row.total_updated_posts),
                "total_duplicates": int(row.total_duplicates),
                "tier_assignments": row.tier_assignments,
            }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    out = Path(__file__).resolve().parents[2] / "reports" / "local-acceptance"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics-latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

