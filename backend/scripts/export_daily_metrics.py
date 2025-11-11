#!/usr/bin/env python3
from __future__ import annotations

"""
Export Daily Metrics to CSV (reports/daily_metrics/YYYY-MM.csv)

Usage:
  cd backend && PYTHONPATH=. python scripts/export_daily_metrics.py [--date YYYY-MM-DD]

Behaviour:
  - Try target date (today if not provided). If no CrawlMetrics exist for that
    date, fallback to the most recent available metric_date in DB.
  - Append one row to CSV; create file with header if not present.
  - Prints the resolved date and output path.
"""

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import asyncio
from sqlalchemy import func, select

from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics
from app.services.metrics.daily_metrics import (
    collect_daily_metrics,
    write_metrics_to_csv,
)


async def _resolve_target_date(preferred: Optional[date]) -> date:
    if preferred is not None:
        return preferred
    # Try today first; if none exists we'll fallback below.
    return datetime.utcnow().date()


async def _fallback_latest_date() -> Optional[date]:
    async with SessionFactory() as session:
        result = await session.execute(select(func.max(CrawlMetrics.metric_date)))
        value = result.scalar()
        if value is None:
            return None
        # value may already be a date
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except Exception:
            return None


async def main() -> int:
    parser = argparse.ArgumentParser(description="Export daily metrics to CSV")
    parser.add_argument("--date", dest="date_str", default=None, help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    preferred: Optional[date] = None
    if args.date_str:
        try:
            preferred = date.fromisoformat(args.date_str)
        except Exception:
            print(f"❌ Invalid --date value: {args.date_str}")
            return 2

    target = await _resolve_target_date(preferred)

    # First try preferred/today
    try:
        metrics = await collect_daily_metrics(target_date=target)
    except Exception:
        # Fallback: pick latest available date from DB
        latest = await _fallback_latest_date()
        if latest is None:
            print("❌ No CrawlMetrics available; cannot export daily metrics")
            return 1
        metrics = await collect_daily_metrics(target_date=latest)
        target = latest

    path = write_metrics_to_csv(metrics)
    print(f"✅ Exported daily metrics for {target.isoformat()} → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

