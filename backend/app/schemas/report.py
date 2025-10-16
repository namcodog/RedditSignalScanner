from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.task import TaskStatus
from app.schemas.analysis import AnalysisRead
from app.schemas.base import ORMModel


class ReportRead(ORMModel):
    id: UUID
    analysis_id: UUID
    html_content: str = Field(min_length=1)
    template_version: str
    generated_at: datetime


class ReportResponse(ORMModel):
    task_id: UUID
    status: TaskStatus
    analysis: AnalysisRead
    report: ReportRead
