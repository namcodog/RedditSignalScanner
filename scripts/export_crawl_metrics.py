#!/usr/bin/env python3
"""导出 crawl_metrics 表数据为 CSV，便于每日追踪命中率与样本量。

Usage:
    PYTHONPATH=backend python3.11 scripts/export_crawl_metrics.py --days 1 --output reports/crawl-metrics-latest.csv
"""
import argparse
import asyncio
import csv
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics


async def fetch_metrics(days: int) -> list[CrawlMetrics]:
    cutoff = date.today() - timedelta(days=days)
    async with SessionFactory() as db:
        result = await db.execute(
            select(CrawlMetrics)
            .where(CrawlMetrics.metric_date >= cutoff)
            .order_by(CrawlMetrics.metric_date.asc(), CrawlMetrics.metric_hour.asc())
        )
        return list(result.scalars().all())


async def main() -> None:
    parser = argparse.ArgumentParser(description="Export crawl_metrics to CSV")
    parser.add_argument("--days", type=int, default=7, help="导出最近 N 天数据 (默认 7)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/crawl-metrics-export.csv"),
        help="输出 CSV 路径",
    )
    args = parser.parse_args()

    metrics = await fetch_metrics(args.days)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "metric_date",
                "metric_hour",
                "cache_hit_rate",
                "valid_posts_24h",
                "total_communities",
                "successful_crawls",
                "empty_crawls",
                "failed_crawls",
                "avg_latency_seconds",
                "created_at",
            ]
        )
        for row in metrics:
            writer.writerow(
                [
                    row.metric_date.isoformat(),
                    row.metric_hour,
                    float(row.cache_hit_rate or 0),
                    row.valid_posts_24h,
                    row.total_communities,
                    row.successful_crawls,
                    row.empty_crawls,
                    row.failed_crawls,
                    float(row.avg_latency_seconds or 0),
                    row.created_at.isoformat(),
                ]
            )

    print(f"导出完成: {args.output} (共 {len(metrics)} 条记录)")


if __name__ == "__main__":
    asyncio.run(main())
