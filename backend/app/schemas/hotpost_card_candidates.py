from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal

from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.hotpost_clues import QuotePreview, ValidationCardDetail, WritingCardDetail
from app.schemas.hotpost_signal import SignalLevel, SourceScopeId, WhyNowReason


TimeWindow = Literal["24h", "7d", "30d"]


class CandidatePack(ORMModel):
    candidate_id: str
    signal_id: str
    source_scope_id: SourceScopeId
    source_scope_name: str
    topic_pack_id:Optional[ str] = None
    topic_cluster_id:Optional[ str] = None
    topic_cluster_ids: list[str] = Field(default_factory=list)
    named_topic_ids: list[str] = Field(default_factory=list)
    query: str
    matched_subreddit: str
    post_id: str
    title: str
    score: int
    num_comments: int
    created_at: datetime
    collected_at: datetime
    collect_batch_id: str
    time_window: TimeWindow
    signal_level: SignalLevel
    why_now_reason: WhyNowReason
    listing_source: str
    primary_reason: str
    matched_keywords: list[str] = Field(default_factory=list)
    top_communities: list[str] = Field(default_factory=list)
    thread_count: int
    community_count: int
    quote_count: int
    intent_tags: list[str] = Field(default_factory=list)
    evidence_quotes: list[QuotePreview] = Field(default_factory=list)


class CandidateImportRequest(ORMModel):
    candidate: CandidatePack


class CandidateDraftRequest(ORMModel):
    card: ValidationCardDetail | WritingCardDetail


class CandidateListResponse(ORMModel):
    items: list[CandidatePack] = Field(default_factory=list)


__all__ = ["CandidateDraftRequest", "CandidateImportRequest", "CandidateListResponse", "CandidatePack", "TimeWindow"]
