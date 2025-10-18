from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class BetaFeedbackCreate(BaseModel):
    """Schema for creating beta feedback."""

    task_id: uuid.UUID = Field(
        ..., description="Task ID for which feedback is provided"
    )
    satisfaction: int = Field(..., ge=1, le=5, description="Satisfaction rating (1-5)")
    missing_communities: List[str] = Field(
        default_factory=list, description="List of missing community names"
    )
    comments: str = Field(default="", description="Additional comments")


class BetaFeedbackResponse(BaseModel):
    """Schema for beta feedback response."""

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    satisfaction: int
    missing_communities: List[str]
    comments: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
