from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.task import TaskStatus
from app.schemas.base import ORMModel, TimestampedModel


class TaskCreate(ORMModel):
    product_description: str = Field(min_length=10, max_length=2000)

    @field_validator("product_description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError(
                "product_description must contain at least 10 non-whitespace characters"
            )
        return cleaned


class TaskRead(TimestampedModel):
    id: UUID
    user_id: UUID
    product_description: str
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
    status: TaskStatus
    product_description: str
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
    error: str | None = None
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
