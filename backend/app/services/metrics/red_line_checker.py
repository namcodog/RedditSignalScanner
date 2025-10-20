"""
Red line monitoring for daily metrics with automatic mitigation strategies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Sequence

import yaml

from app.services.evaluation.threshold_optimizer import update_threshold_config
from app.services.metrics.daily_metrics import DailyMetrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RedLineAction:
    """Represents a mitigation action triggered by a red line."""

    name: str
    description: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class RedLineConfig:
    min_valid_posts: int = 1500
    min_cache_hit_rate: float = 0.6
    max_duplicate_rate: float = 0.2
    min_precision_at_50: float = 0.6
    conservative_threshold_step: float = 0.1
    precision_threshold_step: float = 0.05
    minhash_threshold: float = 0.85
    minhash_floor: float = 0.8


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=True, allow_unicode=True)


def _load_current_threshold(config_path: Path) -> float:
    config = _load_yaml(config_path)
    value = config.get("opportunity_threshold")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.6


def _load_minhash_config(config_path: Path) -> float:
    config = _load_yaml(config_path)
    value = config.get("minhash_threshold")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.85


class RedLineChecker:
    """Evaluate daily metrics against red line thresholds and apply mitigations."""

    def __init__(
        self,
        *,
        config: RedLineConfig | None = None,
        threshold_config_path: Path | None = None,
        dedup_config_path: Path | None = None,
        crawler_trigger: Callable[[], None] | None = None,
    ) -> None:
        self._config = config or RedLineConfig()
        self._threshold_config_path = threshold_config_path or Path(
            "config/thresholds.yaml"
        )
        self._dedup_config_path = dedup_config_path or Path(
            "config/deduplication.yaml"
        )
        self._crawler_trigger = crawler_trigger

    def evaluate(self, metrics: DailyMetrics) -> List[RedLineAction]:
        actions: List[RedLineAction] = []
        actions.extend(self._check_valid_posts(metrics))
        actions.extend(self._check_cache_hit_rate(metrics))
        actions.extend(self._check_duplicate_rate(metrics))
        actions.extend(self._check_precision(metrics))
        return actions

    def _check_valid_posts(self, metrics: DailyMetrics) -> Sequence[RedLineAction]:
        if metrics.valid_posts_24h >= self._config.min_valid_posts:
            return []
        current_threshold = _load_current_threshold(self._threshold_config_path)
        new_threshold = min(
            0.95, current_threshold + self._config.conservative_threshold_step
        )
        update_threshold_config(
            new_threshold,
            config_path=self._threshold_config_path,
        )
        description = (
            "有效帖子不足，已进入保守模式，上调机会阈值 "
            f"{current_threshold:.2f} → {new_threshold:.2f}"
        )
        return [
            RedLineAction(
                name="increase_threshold_conservative_mode",
                description=description,
                metadata={
                    "previous_threshold": round(current_threshold, 4),
                    "new_threshold": round(new_threshold, 4),
                },
            )
        ]

    def _check_cache_hit_rate(self, metrics: DailyMetrics) -> Sequence[RedLineAction]:
        if metrics.cache_hit_rate >= self._config.min_cache_hit_rate:
            return []

        if self._crawler_trigger is not None:
            try:
                self._crawler_trigger()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to trigger supplemental crawl task")
        description = (
            "缓存命中率低于目标，已触发补抓任务以提高抓取频率"
        )
        return [
            RedLineAction(
                name="trigger_supplemental_crawl",
                description=description,
                metadata={
                    "cache_hit_rate": metrics.cache_hit_rate,
                    "threshold": self._config.min_cache_hit_rate,
                },
            )
        ]

    def _check_duplicate_rate(self, metrics: DailyMetrics) -> Sequence[RedLineAction]:
        if metrics.duplicate_rate <= self._config.max_duplicate_rate:
            return []

        current_threshold = _load_minhash_config(self._dedup_config_path)
        new_threshold = max(self._config.minhash_floor, current_threshold - 0.05)
        payload = _load_yaml(self._dedup_config_path)
        payload["minhash_threshold"] = round(new_threshold, 4)
        _write_yaml(self._dedup_config_path, payload)

        description = (
            "重复率过高，已降低 MinHash 阈值 "
            f"{current_threshold:.2f} → {new_threshold:.2f} 减少去重漏网"
        )
        return [
            RedLineAction(
                name="adjust_minhash_threshold",
                description=description,
                metadata={
                    "previous_threshold": round(current_threshold, 4),
                    "new_threshold": round(new_threshold, 4),
                },
            )
        ]

    def _check_precision(self, metrics: DailyMetrics) -> Sequence[RedLineAction]:
        if metrics.precision_at_50 >= self._config.min_precision_at_50:
            return []

        current_threshold = _load_current_threshold(self._threshold_config_path)
        new_threshold = min(
            0.99, current_threshold + self._config.precision_threshold_step
        )
        update_threshold_config(
            new_threshold,
            config_path=self._threshold_config_path,
        )
        description = (
            "Precision@50 低于安全值，已微调机会阈值 "
            f"{current_threshold:.2f} → {new_threshold:.2f}"
        )
        return [
            RedLineAction(
                name="increase_threshold_precision_guard",
                description=description,
                metadata={
                    "previous_threshold": round(current_threshold, 4),
                    "new_threshold": round(new_threshold, 4),
                    "observed_precision": metrics.precision_at_50,
                },
            )
        ]


__all__ = ["RedLineChecker", "RedLineAction", "RedLineConfig"]

