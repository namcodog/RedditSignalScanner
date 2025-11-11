from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class ExamplePost(ORMModel):
    community: str
    content: str
    upvotes: Optional[int] = Field(default=None, ge=0)
    url: Optional[str] = None
    author: Optional[str] = None
    permalink: Optional[str] = None
    duplicate_ids: Optional[list[str]] = Field(default_factory=list)
    evidence_count: Optional[int] = Field(default=None, ge=0)


class PainPoint(ORMModel):
    description: str
    frequency: int = Field(ge=0)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    severity: Literal["low", "medium", "high"]
    example_posts: list[ExamplePost] = Field(default_factory=list)
    user_examples: list[str] = Field(default_factory=list)


class CompetitorSignal(ORMModel):
    name: str
    mentions: int = Field(ge=0)
    sentiment: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    market_share: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    context_snippets: Optional[list[str]] = Field(default_factory=list)
    layer: str = Field(default="summary")


class OpportunitySignal(ORMModel):
    description: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    potential_users: str
    # 数值估计（Spec010）：用于门禁和可调参量化
    potential_users_est: Optional[int] = Field(default=None, ge=0)
    # 关联痛点簇主题（Spec010）：用于“机会挂痛点”显示与审计
    linked_pain_cluster: Optional[str] = None
    # 机会相关热门渠道（Spec010）：摘要/导出可用
    top_channels: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    source_examples: Optional[list[dict[str, Any]]] = Field(default_factory=list)


class EntityMatch(ORMModel):
    name: str
    mentions: int = Field(ge=1)


class EntitySummary(ORMModel):
    brands: list[EntityMatch] = Field(default_factory=list)
    features: list[EntityMatch] = Field(default_factory=list)
    pain_points: list[EntityMatch] = Field(default_factory=list)
    channels: list[EntityMatch] = Field(default_factory=list)
    logistics: list[EntityMatch] = Field(default_factory=list)
    risks: list[EntityMatch] = Field(default_factory=list)


class PainClusterSummary(ORMModel):
    topic: str
    negative_mean: float = Field(ge=-1.0, le=1.0)
    communities_count: int = Field(ge=0)
    top_communities: list[str] = Field(default_factory=list)
    samples: list[str] = Field(default_factory=list)


class LayerTopCompetitor(ORMModel):
    name: str
    mentions: int = Field(ge=0)
    sentiment: Optional[str] = None


class CompetitorLayerSummary(ORMModel):
    layer: str
    label: str
    top_competitors: list[LayerTopCompetitor] = Field(default_factory=list)
    threats: Optional[str] = None


class ChannelBreakdownItem(ORMModel):
    name: str
    mentions: int = Field(ge=0)


class EntityLeaderboardItem(ORMModel):
    name: str
    category: str
    mentions: int = Field(ge=0)


class InsightsPayload(ORMModel):
    pain_points: list[PainPoint]
    competitors: list[CompetitorSignal]
    opportunities: list[OpportunitySignal]
    action_items: list["OpportunityReportOut"] = Field(default_factory=list)
    entity_summary: EntitySummary = Field(default_factory=EntitySummary)
    pain_clusters: list[PainClusterSummary] = Field(default_factory=list)
    competitor_layers_summary: list[CompetitorLayerSummary] = Field(default_factory=list)
    channel_breakdown: list[ChannelBreakdownItem] = Field(default_factory=list)


class CommunitySourceDetail(ORMModel):
    name: str
    categories: list[str] = Field(default_factory=list)
    mentions: int = Field(ge=0)
    daily_posts: int = Field(ge=0)
    avg_comment_length: int = Field(ge=0)
    cache_hit_rate: float = Field(ge=0.0, le=1.0)
    from_cache: bool = False


class EvidenceItemOut(ORMModel):
    title: str
    url: Optional[str] = None
    note: str


class OpportunityReportOut(ORMModel):
    problem_definition: str
    evidence_chain: list[EvidenceItemOut] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    product_fit: float = Field(ge=0.0, le=1.0)
    priority: float = Field(ge=0.0, le=1.0)


class SourcesPayload(ORMModel):
    communities: list[str]
    posts_analyzed: int = Field(ge=0)
    cache_hit_rate: float = Field(ge=0.0, le=1.0)
    analysis_duration_seconds: int | None = Field(default=None, ge=0)
    reddit_api_calls: int | None = Field(default=None, ge=0)
    product_description: Optional[str] = None
    communities_detail: Optional[list[CommunitySourceDetail]] = None
    recovery_strategy: Optional[str] = None
    fallback_quality: Optional[dict[str, Any]] = None
    dedup_stats: Optional[dict[str, Any]] = None
    duplicates_summary: Optional[list[dict[str, Any]]] = Field(default_factory=list)
    # 数据来源注记：例如 "pool" / "pool+discovery" / "cache-only"
    seed_source: Optional[str] = None


class AnalysisRead(ORMModel):
    id: UUID
    task_id: UUID
    insights: InsightsPayload
    sources: SourcesPayload
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1)
    analysis_version: str
    created_at: datetime
