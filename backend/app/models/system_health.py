"""系统健康度与降级记录模型（进程内结构，非 DB 模型）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Degradation:
    component: str
    reason: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    fallback_used: str | None = None


@dataclass(slots=True)
class SystemHealthMetrics:
    # 语义层
    semantic_db_hit_rate: float
    semantic_fallback_count: int
    semantic_load_latency_ms: float
    # 标注层
    labeling_coverage: float
    labeling_quality_score: float
    # 社区层
    tier_distribution: dict[str, float]
    # 分析层
    analysis_success_rate: float
    sample_sufficiency_rate: float
    # 报告层
    report_quality_score: float
    market_mode_usage: float
    degradations: list[Degradation] = field(default_factory=list)

    def add_degradation(self, component: str, reason: str, fallback_used: str | None = None) -> None:
        self.degradations.append(
            Degradation(component=component, reason=reason, fallback_used=fallback_used)
        )
