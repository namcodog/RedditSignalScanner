from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from app.models.task import TaskStatus
from app.schemas.analysis import (
    CommunitySourceDetail,
    CompetitorSignal,
    CompetitorLayerSummary,
    DriverSignal,
    EntitySummary,
    EntityLeaderboardItem,
    OpportunityReportOut,
    OpportunitySignal,
    PainClusterSummary,
    PainPoint,
    ChannelBreakdownItem,
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
    # 头部补充字段：用于前端显示 "Top N of Total" 与来源注记
    total_communities: int = Field(default=0, ge=0)
    top_n: int = Field(default=0, ge=0)
    seed_source: Optional[str] = None


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
    # 可选：LLM 审计字段（启用后端增强时填写）
    llm_used: Optional[bool] = None
    llm_model: Optional[str] = None
    llm_rounds: Optional[int] = Field(default=None, ge=0)
    # 可选：语义词库版本（Spec009/011 对齐，用于报告追溯）
    lexicon_version: Optional[str] = None
    # 可选：市场增强结果（Phase 1 集成），保持向后兼容
    market_enhancements: dict[str, Any] | None = None


class MarketHealth(ORMModel):
    saturation_level: Optional[str] = None
    saturation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ps_ratio: Optional[float] = Field(default=None, ge=0.0)
    ps_ratio_assessment: Optional[str] = None


class ReportContent(ORMModel):
    executive_summary: ReportExecutiveSummary
    pain_points: list[PainPoint] = Field(default_factory=list)
    pain_clusters: list[PainClusterSummary] = Field(default_factory=list)
    competitors: list[CompetitorSignal] = Field(default_factory=list)
    opportunities: list[OpportunitySignal] = Field(default_factory=list)
    action_items: list[OpportunityReportOut] = Field(default_factory=list)
    purchase_drivers: list[DriverSignal] = Field(default_factory=list)
    market_health: Optional[MarketHealth] = None
    entity_summary: EntitySummary = Field(default_factory=EntitySummary)
    entity_leaderboard: list[EntityLeaderboardItem] = Field(default_factory=list)
    competitor_layers_summary: list[CompetitorLayerSummary] = Field(default_factory=list)
    channel_breakdown: list[ChannelBreakdownItem] = Field(default_factory=list)


class LayerCoverageItem(ORMModel):
    layer: str
    posts: int = Field(ge=0)
    hit_posts: int = Field(ge=0)
    coverage: float = Field(ge=0.0, le=1.0)


class MetricsSummary(ORMModel):
    overall: float = Field(ge=0.0, le=1.0)
    brands: float = Field(ge=0.0, le=1.0)
    pain_points: float = Field(ge=0.0, le=1.0)
    top10_unique_share: float = Field(ge=0.0, le=1.0)
    layers: list[LayerCoverageItem] = Field(default_factory=list)


class ReportPayload(ORMModel):
    task_id: UUID
    status: TaskStatus
    generated_at: datetime
    product_description: Optional[str] = None
    data_source: Optional[str] = None
    report_html: Optional[str] = None
    report_structured: dict[str, Any] | None = None
    report: ReportContent
    metadata: ReportMetadata
    overview: ReportOverview
    stats: ReportStats
    # 可选：语义指标摘要（便于前端按需展示）
    metrics_summary: MetricsSummary | None = None


__all__ = [
    "FallbackQuality",
    "ReportContent",
    "ReportExecutiveSummary",
    "MarketHealth",
    "ReportMetadata",
    "ReportOverview",
    "ReportPayload",
    "ReportStats",
    "SentimentBreakdown",
    "TopCommunity",
    "ChannelBreakdownItem",
    "MetricsSummary",
    "LayerCoverageItem",
]
