from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.models.task import TaskStatus
from app.schemas.base import ORMModel, TimestampedModel


AnalysisMode = Literal["market_insight", "operations"]
AuditLevel = Literal["gold", "lab", "noise"]


class TaskCreate(ORMModel):
    product_description: str = Field(min_length=10, max_length=2000)
    example_id: UUID | None = Field(
        default=None,
        description="Optional example library id to reuse a verified report",
    )
    mode: AnalysisMode | None = Field(
        default=None,
        description=(
            "Analysis mode: 'market_insight' or 'operations' (optional, "
            "auto from topic_profile when omitted)"
        ),
    )
    audit_level: AuditLevel | None = Field(
        default=None,
        description="Audit level override: 'gold' | 'lab' | 'noise' (optional)",
    )
    topic_profile_id: str | None = Field(
        default=None,
        description="Optional TopicProfile id to lock the analysis scope",
    )

    @field_validator("product_description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError(
                "product_description must contain at least 10 non-whitespace characters"
            )
        return cleaned

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower()

    @field_validator("audit_level", mode="before")
    @classmethod
    def normalize_audit_level(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower()

    @field_validator("topic_profile_id", mode="before")
    @classmethod
    def normalize_topic_profile_id(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower()

    @field_validator("example_id", mode="before")
    @classmethod
    def normalize_example_id(cls, value: object) -> UUID | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return UUID(cleaned)


class TaskRead(TimestampedModel):
    id: UUID
    user_id: UUID
    product_description: str
    mode: AnalysisMode = "market_insight"
    audit_level: AuditLevel = "lab"
    topic_profile_id: str | None = None
    status: TaskStatus
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    failure_category: str | None = None
    last_retry_at: datetime | None = None
    dead_letter_at: datetime | None = None


class TaskStatusUpdate(ORMModel):
    status: TaskStatus
    error_message: str | None = None


class TaskCreateResponse(ORMModel):
    task_id: UUID
    status: TaskStatus
    created_at: datetime
    estimated_completion: datetime
    sse_endpoint: str


class TaskSummary(ORMModel):
    id: UUID
    user_id: UUID | None = None
    status: TaskStatus
    product_description: str
    mode: AnalysisMode = "market_insight"
    audit_level: AuditLevel = "lab"
    topic_profile_id: str | None = None
    membership_level: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    retry_count: int = 0
    failure_category: str | None = None


class TaskStatusSnapshot(ORMModel):
    task_id: UUID
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: str
    stage: str | None = None
    blocked_reason: str | None = None
    next_action: str | None = None
    details: dict[str, object] | None = None
    error: str | None = None
    percentage: int = Field(ge=0, le=100)
    current_step: str
    sse_endpoint: str
    retry_count: int = 0
    failure_category: str | None = None
    last_retry_at: datetime | None = None
    dead_letter_at: datetime | None = None
    updated_at: datetime


class TaskStatsResponse(ORMModel):
    """Celery task queue statistics."""

    active_workers: int = Field(ge=0, description="Number of active Celery workers")
    active_tasks: int = Field(ge=0, description="Count of tasks currently executing")
    reserved_tasks: int = Field(ge=0, description="Count of tasks reserved by workers")
    scheduled_tasks: int = Field(
        ge=0, description="Count of tasks scheduled for later execution"
    )
    total_tasks: int = Field(
        ge=0, description="Aggregate of active, reserved, and scheduled tasks"
    )



class TaskDiagResponse(ORMModel):
    """运行时配置诊断响应"""

    has_reddit_client: bool = Field(description="Reddit API 客户端是否配置")
    environment: str = Field(description="运行环境（development/production）")
    stalled_tasks_last_run_at: datetime | None = Field(
        default=None, description="卡单看门狗最近一次运行时间"
    )
    stalled_tasks_last_count: int | None = Field(
        default=None, description="卡单看门狗最近一次标记的任务数量"
    )


class TaskSourcesLedgerResponse(ORMModel):
    """任务 sources 账本（用于复盘/演练矩阵，避免依赖 admin 权限）。"""

    task_id: UUID
    status: TaskStatus
    sources: dict[str, object] = Field(default_factory=dict)
