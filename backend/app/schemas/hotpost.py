from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.base import ORMModel


HotpostMode = Literal["trending", "rant", "opportunity"]
HotpostTimeFilter = Literal["week", "month", "year", "all"]


class HotpostSearchRequest(ORMModel):
    """爆帖速递搜索请求"""

    query: str = Field(min_length=2, max_length=2000)
    mode: HotpostMode | None = Field(default=None)
    subreddits: list[str] | None = Field(default=None)
    time_filter: HotpostTimeFilter | None = Field(default=None)
    limit: int = Field(default=30, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("query must contain at least 2 non-whitespace characters")
        return cleaned

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @field_validator("time_filter", mode="before")
    @classmethod
    def normalize_time_filter(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @field_validator("subreddits", mode="before")
    @classmethod
    def normalize_subreddits(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        items = []
        for raw in list(value):
            name = str(raw).strip().lower()
            if not name:
                continue
            if not name.startswith("r/"):
                name = f"r/{name}"
            items.append(name)
        if not items:
            return None
        if len(items) > 10:
            raise ValueError("subreddits最多10个")
        return items


class HotpostComment(ORMModel):
    comment_fullname: str | None = None
    author: str | None = None
    body: str | None = None
    score: int | None = None
    permalink: str | None = None


class Hotpost(ORMModel):
    rank: int
    id: str
    title: str
    body_preview: str | None = None
    score: int
    num_comments: int
    heat_score: int | None = None
    rant_score: float | None = None
    rant_signals: list[str] = Field(default_factory=list)
    resonance_count: int | None = None
    subreddit: str
    author: str | None = None
    reddit_url: str
    created_utc: float
    signals: list[str]
    signal_score: float
    why_relevant: str | None = None
    why_important: str | None = None
    top_comments: list[HotpostComment] = Field(default_factory=list)


class HotpostTopicEvidence(ORMModel):
    title: str
    score: int | None = None
    comments: int | None = None
    subreddit: str | None = None
    url: str | None = None
    key_quote: str | None = None


class HotpostTopic(ORMModel):
    rank: int
    topic: str
    heat_score: int | None = None
    time_trend: str | None = None
    key_takeaway: str | None = None
    evidence: list[HotpostTopicEvidence] = Field(default_factory=list)
    evidence_posts: list["Hotpost"] = Field(default_factory=list)


class PainPoint(ORMModel):
    category: str
    category_en: str | None = None
    description: str | None = None
    mentions: int | None = None
    percentage: float | None = None
    key_takeaway: str | None = None
    severity: str | None = None
    sample_quotes: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    rank: int | None = None
    user_voice: str | None = None
    business_implication: str | None = None
    evidence: list[HotpostTopicEvidence] = Field(default_factory=list)
    evidence_posts: list[Hotpost] = Field(default_factory=list)


class CompetitorMention(ORMModel):
    name: str
    sentiment: str | None = None
    mentions: int | None = None
    sentiment_score: float | None = None
    common_praise: list[str] = Field(default_factory=list)
    common_complaint: list[str] = Field(default_factory=list)
    typical_context: str | None = None
    sample_quote: str | None = None
    vs_adobe: str | None = None
    evidence_quote: str | None = None


class MigrationIntent(ORMModel):
    already_left: str | None = None
    considering: str | None = None
    staying_reluctantly: str | None = None
    total_mentions: int | None = None
    percentage: float | None = None
    status_distribution: dict[str, float] | None = None
    destinations: list[dict[str, object]] = Field(default_factory=list)
    key_quote: str | None = None


class TopQuote(ORMModel):
    quote: str
    score: int | None = None
    subreddit: str | None = None
    url: str | None = None


class CurrentWorkaround(ORMModel):
    solution: str | None = None
    pain: str | None = None
    name: str | None = None
    satisfaction: str | None = None


class UnmetNeedEvidence(ORMModel):
    title: str
    score: int | None = None
    comments: int | None = None
    me_too_comments: int | None = None
    subreddit: str | None = None
    url: str | None = None
    key_quote: str | None = None


class UnmetNeed(ORMModel):
    rank: int | None = None
    need: str
    need_en: str | None = None
    urgency: str | None = None
    mentions: int | None = None
    demand_signal: str | None = None
    me_too_count: int | None = None
    willingness_to_pay: str | None = None
    pay_evidence: str | None = None
    price_range: str | None = None
    key_takeaway: str | None = None
    user_voice: str | None = None
    current_workarounds: list[CurrentWorkaround] = Field(default_factory=list)
    opportunity_insight: str | None = None
    evidence: list[UnmetNeedEvidence] = Field(default_factory=list)
    evidence_posts: list[Hotpost] = Field(default_factory=list)


class ExistingTool(ORMModel):
    name: str
    sentiment: str | None = None
    mentions: int | None = None
    sentiment_score: float | None = None
    common_praise: list[str] = Field(default_factory=list)
    common_complaint: list[str] = Field(default_factory=list)
    praised_for: list[str] = Field(default_factory=list)
    criticized_for: list[str] = Field(default_factory=list)
    gap_analysis: str | None = None


class UserSegment(ORMModel):
    segment: str
    percentage: str | None = None
    core_need: str | None = None
    key_need: str | None = None
    price_sensitivity: str | None = None
    typical_quote: str | None = None


class MarketOpportunity(ORMModel):
    gap: str | None = None
    target_user: str | None = None
    pricing_hint: str | None = None
    gtm_channel: str | None = None
    strength: str | None = None
    unmet_gap: str | None = None
    demand_signal: str | None = None
    competition_level: str | None = None
    recommendation: str | None = None


class NextSteps(ORMModel):
    deepdive_available: bool | None = None
    deepdive_token: str | None = None
    suggested_keywords: list[str] = Field(default_factory=list)


class HotpostSearchResponse(ORMModel):
    query_id: str
    query: str
    mode: HotpostMode
    search_time: datetime
    from_cache: bool
    status: str | None = None
    position: int | None = None
    estimated_wait_seconds: int | None = None
    summary: str
    markdown_report: str | None = None
    top_posts: list[Hotpost]
    key_comments: list[HotpostComment]
    top_rants: list[Hotpost] | None = None
    top_discovery_posts: list[Hotpost] | None = None
    pain_points: list[PainPoint] | None = None
    opportunities: list[dict[str, Any]] | None = None
    trending_keywords: list[str] | None = None
    topics: list[HotpostTopic] | None = None
    competitor_mentions: list[CompetitorMention] | None = None
    migration_intent: MigrationIntent | None = None
    top_quotes: list[TopQuote] | None = None
    unmet_needs: list[UnmetNeed] | None = None
    existing_tools: list[ExistingTool] | None = None
    user_segments: list[UserSegment] | None = None
    market_opportunity: MarketOpportunity | None = None
    communities: list[str]
    related_queries: list[str]
    evidence_count: int
    community_distribution: dict[str, str]
    sentiment_overview: dict[str, float]
    rant_intensity: dict[str, float] | None = None
    need_urgency: dict[str, float] | None = None
    opportunity_strength: str | None = None
    confidence: str
    reliability_note: str | None = None
    next_steps: NextSteps | None = None
    notes: list[str] | None = None
    debug_info: dict[str, Any] | None = None


class HotpostDeepdiveResponse(ORMModel):
    deepdive_token: str
    expires_in_seconds: int


class HotpostDeepdiveRequest(ORMModel):
    query_id: str
    product_desc: str | None = None
    seed_subreddits: list[str] | None = None


__all__ = [
    "HotpostMode",
    "HotpostTimeFilter",
    "HotpostSearchRequest",
    "HotpostSearchResponse",
    "HotpostDeepdiveResponse",
    "HotpostDeepdiveRequest",
    "Hotpost",
    "HotpostComment",
    "HotpostTopic",
    "HotpostTopicEvidence",
    "PainPoint",
    "CompetitorMention",
    "MigrationIntent",
    "TopQuote",
    "UnmetNeed",
    "UnmetNeedEvidence",
    "CurrentWorkaround",
    "ExistingTool",
    "UserSegment",
    "MarketOpportunity",
    "NextSteps",
]
