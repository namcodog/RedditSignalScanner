from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.base import ORMModel


MonitoringStatus = Literal["ok", "degraded", "error"]


class MonitoringDegradedCheck(ORMModel):
    code: str
    message: str


class MonitoringAlertPayload(ORMModel):
    level: str
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MonitoringTaskResult(ORMModel):
    status: MonitoringStatus
    generated_at: datetime | None = None
    message: str | None = None
    degraded_checks: list[MonitoringDegradedCheck] = Field(default_factory=list)


class CacheHealthResult(MonitoringTaskResult):
    seed_count: int | None = None
    cache_hit_rate: float | None = None
    entity_rate_60m: float | None = None
    recent_posts_60m: int | None = None
    recent_entities_60m: int | None = None
    cleanup_deleted: int | None = None
    storage_metrics_id: int | None = None


class ContractHealthResult(MonitoringTaskResult):
    window_hours: int | None = None
    report: dict[str, Any] | None = None
    alerts: list[MonitoringAlertPayload] = Field(default_factory=list)


__all__ = [
    "CacheHealthResult",
    "ContractHealthResult",
    "MonitoringAlertPayload",
    "MonitoringDegradedCheck",
    "MonitoringStatus",
    "MonitoringTaskResult",
]
