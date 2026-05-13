from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import Field, model_validator

from app.schemas.base import ORMModel
from app.schemas.hotpost_card_candidates import TimeWindow
from app.schemas.hotpost_clues import CardLane, CardType, QuotePreview, WritingDetail
from app.schemas.hotpost_signal import SignalLevel, SourceScopeId, WhyNowReason
from app.schemas.hotpost_validate_details import ValidationDetailLike, normalize_validation_container_payload, validate_validation_detail_lane


DraftStatus = Literal["draft"]


class DraftBase(ORMModel):
    draft_id: str
    candidate_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    card_id: str
    signal_id: str
    topic_pack_id:Optional[ str] = None
    topic_cluster_id:Optional[ str] = None
    topic_cluster_ids: list[str] = Field(default_factory=list)
    named_topic_ids: list[str] = Field(default_factory=list)
    card_type: CardType
    lane: CardLane = "signal"
    category_id: str
    title: str
    source_scope_id: SourceScopeId
    source_scope_name: str
    matched_subreddit: str
    post_id: str
    source_event_at:Optional[ datetime] = None
    score: int
    num_comments: int
    time_window: TimeWindow
    signal_level: SignalLevel
    why_now_reason: WhyNowReason
    thread_count: int
    community_count: int
    quote_count: int
    intent_tags: list[str] = Field(default_factory=list)
    evidence_quotes: list[QuotePreview] = Field(default_factory=list)
    summary_line: str = ""
    audience: str = ""
    why_now: str = ""
    source_link: str = ""
    source_links: list[str] = Field(default_factory=list)
    source_communities: list[str] = Field(default_factory=list)
    draft_status: DraftStatus = "draft"
    draft_note:Optional[ str] = None


class ValidationCardDraft(DraftBase):
    detail: ValidationDetailLike

    @model_validator(mode="before")
    @classmethod
    def _normalize_detail_for_lane(cls, payload: Any) -> Any:
        return normalize_validation_container_payload(payload)

    @model_validator(mode="after")
    def _validate_detail_for_lane(self) -> "ValidationCardDraft":
        validate_validation_detail_lane(self.lane, self.detail)
        return self


class WritingCardDraft(DraftBase):
    detail: WritingDetail


class DraftSeedRequest(ORMModel):
    card_type: CardType


class DraftImportRequest(ORMModel):
    card: ValidationCardDraft | WritingCardDraft


class DraftListResponse(ORMModel):
    items: list[ValidationCardDraft | WritingCardDraft] = Field(default_factory=list)


class DraftPublishResponse(ORMModel):
    card_id: str
    published_count: int


__all__ = [
    "DraftImportRequest",
    "DraftListResponse",
    "DraftPublishResponse",
    "DraftSeedRequest",
    "ValidationCardDraft",
    "WritingCardDraft",
]
