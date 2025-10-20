"""Celery task for generating daily metrics reports."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.core.celery_app import celery_app
from app.services.metrics.daily_metrics import (
    collect_daily_metrics,
    write_metrics_to_csv,
)
from app.services.metrics.red_line_checker import RedLineChecker

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.metrics.generate_daily")
def generate_daily_metrics_task(
    *,
    labeled_data_path: str | None = None,
    threshold_config_path: str | None = None,
    dedup_config_path: str | None = None,
    output_directory: str | None = None,
) -> str:
    """Collect and persist daily metrics."""
    metrics = asyncio.run(
        collect_daily_metrics(
            labeled_data_path=Path(labeled_data_path) if labeled_data_path else None,
            threshold_config_path=Path(threshold_config_path)
            if threshold_config_path
            else None,
        )
    )
    csv_path = write_metrics_to_csv(
        metrics,
        output_directory=Path(output_directory) if output_directory else Path("reports/daily_metrics"),
    )

    def _trigger_supplemental_crawl() -> None:
        try:
            celery_app.send_task("tasks.crawler.crawl_seed_communities")
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Unable to trigger supplemental crawl task")

    checker = RedLineChecker(
        threshold_config_path=Path(threshold_config_path)
        if threshold_config_path
        else Path("config/thresholds.yaml"),
        dedup_config_path=Path(dedup_config_path)
        if dedup_config_path
        else Path("config/deduplication.yaml"),
        crawler_trigger=_trigger_supplemental_crawl,
    )
    actions = checker.evaluate(metrics)
    for action in actions:
        logger.warning("Red line triggered: %s", action.description, extra=action.metadata)

    logger.info(
        "Daily metrics generated",
        extra={
            "metrics_date": metrics.date.isoformat(),
            "csv_path": str(csv_path),
            "cache_hit_rate": metrics.cache_hit_rate,
            "precision_at_50": metrics.precision_at_50,
        },
    )
    return str(csv_path)
