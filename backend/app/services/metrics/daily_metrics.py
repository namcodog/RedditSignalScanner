"""Daily metrics collection utilities for automated reporting."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional
import yaml
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics
from app.services.evaluation.threshold_optimizer import (
    calculate_precision_at_k,
    score_posts,
)
from app.services.labeling import load_labeled_data


@dataclass
class DailyMetrics:
    date: date
    cache_hit_rate: float
    valid_posts_24h: int
    total_communities: int
    duplicate_rate: float
    precision_at_50: float
    avg_score: float


def _default_labeled_path(path: Optional[Path]) -> Path:
    return path or Path("data/labeled_samples.csv")


def _default_threshold_path(path: Optional[Path]) -> Path:
    return path or Path("config/thresholds.yaml")


def _load_threshold(config_path: Path) -> float:
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
            value = payload.get("opportunity_threshold")
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
    return 0.6


async def _fetch_crawl_metrics(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    target_date: date,
) -> list[CrawlMetrics]:
    query: Select[tuple[CrawlMetrics]] = select(CrawlMetrics).where(
        CrawlMetrics.metric_date == target_date
    )
    async with session_factory() as session:
        result = await session.execute(query)
        return list(result.scalars())


def _compute_duplicate_rate(
    total_new: int,
    total_updated: int,
    total_duplicates: int,
) -> float:
    denominator = total_new + total_updated + total_duplicates
    if denominator == 0:
        return 0.0
    return float(total_duplicates / denominator)


async def collect_daily_metrics(
    *,
    target_date: Optional[date] = None,
    labeled_data_path: Optional[Path] = None,
    threshold_config_path: Optional[Path] = None,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> DailyMetrics:
    """Aggregate crawl metrics and compute scoring KPIs for the given date."""
    evaluation_date = target_date or datetime.now(timezone.utc).date()
    records = await _fetch_crawl_metrics(
        session_factory=session_factory,
        target_date=evaluation_date,
    )
    if not records:
        raise ValueError(f"No crawl metrics available for {evaluation_date.isoformat()}")

    cache_rates = [float(record.cache_hit_rate) for record in records]
    cache_hit_rate = float(mean(cache_rates))
    valid_posts = sum(int(record.valid_posts_24h) for record in records)
    total_communities = sum(int(record.total_communities) for record in records)
    total_new = sum(int(record.total_new_posts) for record in records)
    total_updated = sum(int(record.total_updated_posts) for record in records)
    total_duplicates = sum(int(record.total_duplicates) for record in records)
    duplicate_rate = _compute_duplicate_rate(total_new, total_updated, total_duplicates)

    labeled_csv = _default_labeled_path(labeled_data_path)
    threshold_path = _default_threshold_path(threshold_config_path)
    threshold = _load_threshold(threshold_path)

    precision_at_50 = 0.0
    avg_score = 0.0

    if labeled_csv.exists():
        try:
            labeled_df = load_labeled_data(labeled_csv)
            if not labeled_df.empty:
                scored_df = score_posts(labeled_df)
                precision_at_50 = calculate_precision_at_k(
                    scored_df, threshold=threshold, k=50
                )
                avg_score = float(scored_df["predicted_score"].mean())
        except Exception:
            # Swallow exceptions to avoid breaking the metrics pipeline
            precision_at_50 = 0.0
            avg_score = 0.0

    return DailyMetrics(
        date=evaluation_date,
        cache_hit_rate=round(cache_hit_rate, 4),
        valid_posts_24h=valid_posts,
        total_communities=total_communities,
        duplicate_rate=round(duplicate_rate, 4),
        precision_at_50=round(precision_at_50, 4),
        avg_score=round(avg_score, 4),
    )


def write_metrics_to_csv(
    metrics: DailyMetrics,
    output_directory: Path = Path("reports/daily_metrics"),
) -> Path:
    """Append the daily metrics to the YYYY-MM.csv report file."""
    output_directory.mkdir(parents=True, exist_ok=True)
    file_path = output_directory / f"{metrics.date:%Y-%m}.csv"
    fieldnames = [
        "date",
        "cache_hit_rate",
        "valid_posts_24h",
        "total_communities",
        "duplicate_rate",
        "precision_at_50",
        "avg_score",
    ]
    row = {
        "date": metrics.date.isoformat(),
        "cache_hit_rate": metrics.cache_hit_rate,
        "valid_posts_24h": metrics.valid_posts_24h,
        "total_communities": metrics.total_communities,
        "duplicate_rate": metrics.duplicate_rate,
        "precision_at_50": metrics.precision_at_50,
        "avg_score": metrics.avg_score,
    }

    file_exists = file_path.exists()
    with file_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    return file_path
