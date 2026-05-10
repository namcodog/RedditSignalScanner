from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import Field, model_validator

from app.schemas.base import ORMModel
from app.schemas.hotpost_signal import SignalLevel, SourceScopeId, ToneTag, WhyNowReason
from app.schemas.hotpost_validate_details import (
    HotValidationDetail,
    SignalValidationDetail,
    ValidationDetailLike,
    normalize_validation_container_payload,
    validate_validation_detail_lane,
)


CardType = Literal["validate", "write"]
CardListType = Literal["all", "validate", "write", "hot", "supplement"]
CardLane = Literal["signal", "hot", "breakdown"]
CardEventType = Literal[
    "home_view",
    "detail_view",
    "back_click",
    "origin_click",
    "quote_click",
    "share_click",
    "category_click",
    "type_click",
    "favorite_click",
    "favorites_view",
    "profile_view",
    "tab_click",
    "card_open_click",
    "home_filter_click",
    "load_more_click",
    "history_card_click",
    "history_retry_click",
    "history_login_click",
    "history_home_click",
    "detail_read_toggle_click",
    "detail_read_next_click",
    "detail_invite_back_click",
    "detail_invite_share_click",
    "points_back_click",
    "points_login_click",
    "points_invite_click",
    "points_rules_click",
    "points_ledger_click",
    "profile_points_click",
    "profile_checkin_click",
    "profile_favorites_click",
    "profile_feedback_click",
    "profile_login_click",
    "profile_phone_click",
    "profile_logout_click",
    "phone_leave_click",
    "phone_login_click",
    "phone_consent_click",
    "phone_terms_click",
    "phone_privacy_click",
    "phone_bind_click",
    "phone_avatar_click",
    "phone_profile_save_click",
    "legal_back_click",
]


class Category(ORMModel):
    category_id: str
    title: str
    description: str


class QuotePreview(ORMModel):
    text: str
    community: str
    permalink: str


class SourceModule(ORMModel):
    primary_communities: list[str] = Field(default_factory=list)
    top_community: str
    tone_tags: list[ToneTag] = Field(default_factory=list)
    thread_count: int
    community_count: int
    last_active_text: str


class ControversyChart(ORMModel):
    support_ratio: float
    oppose_ratio: float
    neutral_ratio: float
    support_point: str
    oppose_point: str
    neutral_point: str
    debate_focus: str
    dominant_side: Literal["support", "oppose", "neutral"]
    confidence: Literal["low", "medium", "high"]


class ControversyMeta(ORMModel):
    post_id: str
    sample_size: int
    sampled_at: Optional[datetime] = None
    fetch_status: str
    llm_summary_version: str
    sample_quality: str
    summary_status: str
    confidence_reason: Optional[str] = None


class CardSummary(ORMModel):
    card_id: str
    signal_id: str
    card_type: CardType
    lane: CardLane = "signal"
    category_id: str
    source_scope_id: SourceScopeId
    source_scope_name: str
    topic_pack_id:Optional[ str] = None
    topic_cluster_id:Optional[ str] = None
    topic_cluster_ids: list[str] = Field(default_factory=list)
    named_topic_ids: list[str] = Field(default_factory=list)
    source_domain_id: str
    source_domain_name: str
    source_event_at:Optional[ datetime] = None
    title: str
    summary_line: str
    audience: str
    why_now: str
    why_now_reason: WhyNowReason
    signal_level:Optional[ SignalLevel] = None
    intent_tags: list[str] = Field(default_factory=list)
    top_community: str
    thread_count: int
    community_count: int
    source_module: Optional[SourceModule] = None
    preview_quote: QuotePreview
    published_at: datetime
    controversy_chart:Optional[ ControversyChart] = None
    controversy_meta:Optional[ ControversyMeta] = None


ValidationDetail = SignalValidationDetail


class WritingDetail(ORMModel):
    thesis: str
    writing_angle_or_perspective: str
    tension_point_or_why_it_matters: str
    title_hooks: list[str] = Field(default_factory=list)
    quote_pack: list[str] = Field(default_factory=list)


class ValidationCardDetail(CardSummary):
    source_module: SourceModule
    quotes: list[QuotePreview] = Field(default_factory=list)
    source_link: str
    detail: ValidationDetailLike

    @model_validator(mode="before")
    @classmethod
    def _normalize_detail_for_lane(cls, payload: Any) -> Any:
        return normalize_validation_container_payload(payload)

    @model_validator(mode="after")
    def _validate_detail_for_lane(self) -> "ValidationCardDetail":
        validate_validation_detail_lane(self.lane, self.detail)
        return self


class WritingCardDetail(CardSummary):
    source_module: SourceModule
    quotes: list[QuotePreview] = Field(default_factory=list)
    source_link: str
    detail: WritingDetail


class CategoryListResponse(ORMModel):
    items: list[Category] = Field(default_factory=list)


class CardListResponse(ORMModel):
    items: list[CardSummary] = Field(default_factory=list)
    next_cursor:Optional[ str] = None


class CardEventRequest(ORMModel):
    type: CardEventType
    card_id:Optional[ str] = None
    category_id:Optional[ str] = None


class CardEventResponse(ORMModel):
    ok: bool = True


__all__ = [
    "CardEventRequest",
    "CardEventResponse",
    "CardListResponse",
    "CardListType",
    "CardLane",
    "CardSummary",
    "Category",
    "CategoryListResponse",
    "ControversyChart",
    "ControversyMeta",
    "HotValidationDetail",
    "ValidationCardDetail",
    "ValidationDetail",
    "WritingCardDetail",
]
