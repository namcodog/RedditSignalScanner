from __future__ import annotations

import asyncio
import types

import pytest

from app.core.celery_app import celery_app
from app.services.adaptive_crawler import AdaptiveCrawler, AdaptiveCrawlerConfig


class _FakeMetrics:
    def __init__(self, rate: float) -> None:
        self._rate = rate

    async def calculate_hit_rate(self, *, window_minutes: int = 60) -> float:  # type: ignore[override]
        return self._rate


@pytest.mark.asyncio
async def test_adjust_sets_interval_to_4h_when_hit_rate_gt_90pct() -> None:
    crawler = AdaptiveCrawler(metrics=_FakeMetrics(0.95))
    hours = await crawler.adjust_crawl_frequency()
    assert hours == 4
    assert celery_app.conf.get("adaptive_crawl_hours") == 4


@pytest.mark.asyncio
async def test_adjust_sets_interval_to_1h_when_hit_rate_lt_70pct() -> None:
    crawler = AdaptiveCrawler(metrics=_FakeMetrics(0.5))
    hours = await crawler.adjust_crawl_frequency()
    assert hours == 1
    assert celery_app.conf.get("adaptive_crawl_hours") == 1


@pytest.mark.asyncio
async def test_adjust_sets_interval_to_2h_when_hit_rate_between_70_and_90pct() -> None:
    crawler = AdaptiveCrawler(metrics=_FakeMetrics(0.8))
    hours = await crawler.adjust_crawl_frequency()
    assert hours == 2
    assert celery_app.conf.get("adaptive_crawl_hours") == 2

