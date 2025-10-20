from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

import pytest

import yaml

from app.services.metrics.daily_metrics import DailyMetrics
from app.services.metrics.red_line_checker import (
    RedLineChecker,
    RedLineConfig,
)


def _make_metrics(
    *,
    cache_hit_rate: float = 0.7,
    valid_posts_24h: int = 2000,
    total_communities: int = 40,
    duplicate_rate: float = 0.05,
    precision_at_50: float = 0.65,
    avg_score: float = 0.55,
) -> DailyMetrics:
    return DailyMetrics(
        date=date(2025, 10, 20),
        cache_hit_rate=cache_hit_rate,
        valid_posts_24h=valid_posts_24h,
        total_communities=total_communities,
        duplicate_rate=duplicate_rate,
        precision_at_50=precision_at_50,
        avg_score=avg_score,
    )


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_valid_posts_red_line_raises_threshold(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    _write_yaml(thresholds, "opportunity_threshold: 0.6\n")
    checker = RedLineChecker(
        config=RedLineConfig(),
        threshold_config_path=thresholds,
        dedup_config_path=tmp_path / "dedup.yaml",
    )
    metrics = _make_metrics(valid_posts_24h=1200)
    actions = checker.evaluate(metrics)
    assert any(action.name == "increase_threshold_conservative_mode" for action in actions)
    threshold_value = yaml.safe_load(thresholds.read_text(encoding="utf-8"))
    assert pytest.approx(0.7, rel=1e-3) == threshold_value["opportunity_threshold"]


def test_low_cache_hit_rate_triggers_crawl(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    dedup = tmp_path / "dedup.yaml"
    _write_yaml(thresholds, "opportunity_threshold: 0.6\n")
    _write_yaml(dedup, "minhash_threshold: 0.85\n")

    triggered: List[str] = []

    def fake_trigger() -> None:
        triggered.append("called")

    checker = RedLineChecker(
        threshold_config_path=thresholds,
        dedup_config_path=dedup,
        crawler_trigger=fake_trigger,
    )
    metrics = _make_metrics(cache_hit_rate=0.4)
    actions = checker.evaluate(metrics)
    assert triggered == ["called"]
    assert any(action.name == "trigger_supplemental_crawl" for action in actions)


def test_high_duplicate_rate_adjusts_minhash(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    dedup = tmp_path / "dedup.yaml"
    _write_yaml(thresholds, "opportunity_threshold: 0.65\n")
    _write_yaml(dedup, "minhash_threshold: 0.85\n")

    checker = RedLineChecker(
        threshold_config_path=thresholds,
        dedup_config_path=dedup,
    )
    metrics = _make_metrics(duplicate_rate=0.35)
    actions = checker.evaluate(metrics)
    assert any(action.name == "adjust_minhash_threshold" for action in actions)
    dedup_value = yaml.safe_load(dedup.read_text(encoding="utf-8"))
    assert pytest.approx(0.8, rel=1e-3) == dedup_value["minhash_threshold"]


def test_low_precision_adjusts_threshold(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    dedup = tmp_path / "dedup.yaml"
    _write_yaml(thresholds, "opportunity_threshold: 0.7\n")
    _write_yaml(dedup, "minhash_threshold: 0.8\n")
    checker = RedLineChecker(
        threshold_config_path=thresholds,
        dedup_config_path=dedup,
    )
    metrics = _make_metrics(precision_at_50=0.4, duplicate_rate=0.05)
    actions = checker.evaluate(metrics)
    assert any(action.name == "increase_threshold_precision_guard" for action in actions)
    assert "0.75" in thresholds.read_text(encoding="utf-8")
