from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class DecisionUnitEvidence(ORMModel):
    id: UUID
    post_url: str = Field(max_length=500)
    excerpt: str
    timestamp: datetime
    subreddit: str = Field(max_length=100)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    content_type: str | None = Field(default=None, max_length=16)
    content_id: int | None = None


class DecisionUnitSummary(ORMModel):
    id: UUID
    task_id: UUID
    title: str = Field(max_length=500)
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    time_window_days: int = Field(gt=0)
    subreddits: list[str] = Field(default_factory=list)
    concept_id: int | None = None
    signal_type: str | None = Field(default=None, max_length=20)
    du_schema_version: int | None = None
    du_payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DecisionUnitDetail(DecisionUnitSummary):
    evidence: list[DecisionUnitEvidence] = Field(default_factory=list)


class DecisionUnitListResponse(ORMModel):
    total: int = Field(ge=0)
    items: list[DecisionUnitSummary] = Field(default_factory=list)


class DecisionUnitFeedbackCreate(ORMModel):
    label: str = Field(
        ...,
        max_length=20,
        description="反馈标签：correct/incorrect/mismatch/valuable/worthless",
    )
    evidence_id: UUID | None = Field(
        default=None,
        description="可选：绑定某条证据（缺省时由服务端选择该 DecisionUnit 的 top evidence）",
    )
    note: str | None = Field(default=None, max_length=2000)
    meta: dict[str, object] = Field(default_factory=dict)


class DecisionUnitFeedback(ORMModel):
    id: UUID
    decision_unit_id: UUID
    task_id: UUID
    topic_profile_id: str | None = None
    user_id: UUID
    evidence_id: UUID | None = None
    label: str = Field(max_length=20)
    note: str
    meta: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


__all__ = [
    "DecisionUnitDetail",
    "DecisionUnitEvidence",
    "DecisionUnitListResponse",
    "DecisionUnitSummary",
    "DecisionUnitFeedbackCreate",
    "DecisionUnitFeedback",
]
