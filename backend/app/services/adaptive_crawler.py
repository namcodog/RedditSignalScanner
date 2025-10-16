from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from celery.schedules import crontab

from app.core.celery_app import celery_app
from app.services.cache_metrics import CacheMetrics


class CacheMetricsLike(Protocol):
    async def calculate_hit_rate(self, *, window_minutes: int = 60) -> float: ...


@dataclass
class AdaptiveCrawlerConfig:
    schedule_key: str = "warmup-crawl-seed-communities"
    window_minutes: int = 60


class AdaptiveCrawler:
    """
    Adjust Celery Beat schedule based on cache hit rate.

    Policy:
    - hit_rate > 0.9  -> every 4 hours
    - 0.7 <= hit_rate <= 0.9 -> every 2 hours
    - hit_rate < 0.7  -> every 1 hour
    """

    def __init__(self, metrics: CacheMetricsLike | None = None, *, config: AdaptiveCrawlerConfig | None = None) -> None:
        self._metrics: CacheMetricsLike = metrics or CacheMetrics()
        self._conf = config or AdaptiveCrawlerConfig()

    async def adjust_crawl_frequency(self) -> int:
        """Compute current hit rate and update Celery Beat schedule.

        Returns the new interval in hours.
        """
        rate = await self._metrics.calculate_hit_rate(window_minutes=self._conf.window_minutes)
        if rate > 0.9:
            hours = 4
        elif rate < 0.7:
            hours = 1
        else:
            hours = 2
        self.set_crawl_interval(hours)
        return hours

    # Separated for testability (can be called directly)
    def set_crawl_interval(self, hours: int) -> None:
        """Update Beat schedule for the warmup crawler.

        This mutates celery_app.conf.beat_schedule and records the chosen interval
        under key 'adaptive_crawl_hours' for observability/testing.
        """
        key = self._conf.schedule_key
        entry = celery_app.conf.beat_schedule.get(key)
        if entry is None:
            # create a new entry if missing
            entry = {
                "task": "tasks.crawler.crawl_seed_communities",
                "schedule": crontab(minute="0", hour=f"*/{hours}"),
            }
            celery_app.conf.beat_schedule[key] = entry
        else:
            entry["schedule"] = crontab(minute="0", hour=f"*/{hours}")
        # record chosen hours so tests can assert
        celery_app.conf.update({"adaptive_crawl_hours": hours})


__all__ = ["AdaptiveCrawler", "AdaptiveCrawlerConfig"]

