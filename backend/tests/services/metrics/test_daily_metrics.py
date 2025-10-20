from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import delete

from app.db.session import SessionFactory
from app.models.crawl_metrics import CrawlMetrics
from app.services.metrics.daily_metrics import (
    DailyMetrics,
    collect_daily_metrics,
    write_metrics_to_csv,
)


async def _seed_crawl_metrics(metric_date: date) -> None:
    async with SessionFactory() as session:
        await session.execute(delete(CrawlMetrics))
        records = [
            CrawlMetrics(
                metric_date=metric_date,
                metric_hour=hour,
                cache_hit_rate=0.6 + (hour * 0.01),
                valid_posts_24h=100 + hour,
                total_communities=10 + hour,
                total_new_posts=50 + hour,
                total_updated_posts=25 + hour,
                total_duplicates=5 + hour,
            )
            for hour in range(3)
        ]
        session.add_all(records)
        await session.commit()


def _create_labeled_data(path: Path) -> None:
    df = pd.DataFrame(
        [
            {
                "post_id": "p1",
                "title": "Great opportunity",
                "body": "Looking for automation tools",
                "subreddit": "r/startups",
                "score": 42,
                "label": "opportunity",
                "strength": "strong",
                "notes": "",
            },
            {
                "post_id": "p2",
                "title": "General chat",
                "body": "Just hanging out",
                "subreddit": "r/chat",
                "score": 5,
                "label": "non-opportunity",
                "strength": "weak",
                "notes": "",
            },
        ]
    )
    df.to_csv(path, index=False)


@pytest.mark.asyncio
async def test_collect_daily_metrics_aggregates_expected_values(tmp_path: Path) -> None:
    target_date = date.today()
    await _seed_crawl_metrics(target_date)
    labeled_path = tmp_path / "labeled.csv"
    _create_labeled_data(labeled_path)
    threshold_path = tmp_path / "thresholds.yaml"
    threshold_path.write_text("opportunity_threshold: 0.5\n", encoding="utf-8")

    metrics = await collect_daily_metrics(
        target_date=target_date,
        labeled_data_path=labeled_path,
        threshold_config_path=threshold_path,
        session_factory=SessionFactory,
    )

    assert isinstance(metrics, DailyMetrics)
    assert metrics.valid_posts_24h > 0
    assert metrics.cache_hit_rate > 0
    assert 0.0 <= metrics.precision_at_50 <= 1.0
    assert metrics.avg_score > 0


def test_write_metrics_to_csv_creates_monthly_report(tmp_path: Path) -> None:
    metrics = DailyMetrics(
        date=date(2025, 10, 20),
        cache_hit_rate=0.75,
        valid_posts_24h=320,
        total_communities=45,
        duplicate_rate=0.12,
        precision_at_50=0.65,
        avg_score=0.58,
    )
    path = write_metrics_to_csv(metrics, tmp_path)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "2025-10-20" in content

