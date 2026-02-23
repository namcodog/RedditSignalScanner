"""Semantic provider interfaces for decoupled lexical access."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, Optional


class SemanticLoadStrategy(Enum):
    DB_ONLY = "db_only"
    DB_YAML_FALLBACK = "fallback"
    YAML_ONLY = "yaml_only"


@dataclass(slots=True)
class SemanticMetrics:
    db_hits: int
    yaml_fallbacks: int
    cache_hit_rate: float
    last_refresh: Optional[datetime | str]
    total_terms: int
    load_latency_p95_ms: float


class SemanticProvider(Protocol):
    """语义库提供者接口，隔离实现细节。"""

    async def load(self):
        """加载语义库，返回统一词库对象（实现方自定义类型）。"""

    async def reload(self) -> None:
        """强制刷新缓存/重新加载。"""

    async def get_metrics(self) -> SemanticMetrics:
        """返回运行指标。"""
