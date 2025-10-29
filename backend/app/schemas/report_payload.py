from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from app.models.task import TaskStatus
from app.schemas.analysis import (
    CommunitySourceDetail,
    CompetitorSignal,
    EntitySummary,
    OpportunityReportOut,
    OpportunitySignal,
    PainPoint,
)
from app.schemas.base import ORMModel


class ReportStats(ORMModel):
    total_mentions: int = Field(ge=0)
    positive_mentions: int = Field(ge=0)
    negative_mentions: int = Field(ge=0)
    neutral_mentions: int = Field(ge=0)


class SentimentBreakdown(ORMModel):
    positive: int = Field(ge=0, le=100)
    negative: int = Field(ge=0, le=100)
    neutral: int = Field(ge=0, le=100)


class TopCommunity(ORMModel):
    name: str
    mentions: int = Field(ge=0)
    relevance: int = Field(ge=0, le=100)
    category: Optional[str] = None
    daily_posts: Optional[int] = Field(default=None, ge=0)
    avg_comment_length: Optional[int] = Field(default=None, ge=0)
    from_cache: bool = False
    members: Optional[int] = Field(default=None, ge=0)


class ReportOverview(ORMModel):
    sentiment: SentimentBreakdown
    top_communities: list[TopCommunity] = Field(default_factory=list)


class ReportExecutiveSummary(ORMModel):
    total_communities: int = Field(ge=0)
    key_insights: int = Field(ge=0)
    top_opportunity: str


class FallbackQuality(ORMModel):
    cache_coverage: float = Field(ge=0.0, le=1.0)
    data_freshness_hours: float = Field(ge=0.0)
    estimated_accuracy: float = Field(ge=0.0, le=1.0)


class ReportMetadata(ORMModel):
    analysis_version: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time_seconds: float = Field(ge=0.0)
    cache_hit_rate: float = Field(ge=0.0, le=1.0)
    total_mentions: int = Field(ge=0)
    recovery_applied: Optional[str] = None
    fallback_quality: Optional[FallbackQuality] = None


class ReportContent(ORMModel):
    executive_summary: ReportExecutiveSummary
    pain_points: list[PainPoint] = Field(default_factory=list)
    competitors: list[CompetitorSignal] = Field(default_factory=list)
    opportunities: list[OpportunitySignal] = Field(default_factory=list)
    action_items: list[OpportunityReportOut] = Field(default_factory=list)
    entity_summary: EntitySummary = Field(default_factory=EntitySummary)


class ReportPayload(ORMModel):
    task_id: UUID
    status: TaskStatus
    generated_at: datetime
    product_description: Optional[str] = None
    report_html: Optional[str] = None
    report: ReportContent
    metadata: ReportMetadata
    overview: ReportOverview
    stats: ReportStats


__all__ = [
    "FallbackQuality",
    "ReportContent",
    "ReportExecutiveSummary",
    "ReportMetadata",
    "ReportOverview",
    "ReportPayload",
    "ReportStats",
    "SentimentBreakdown",
    "TopCommunity",
]
