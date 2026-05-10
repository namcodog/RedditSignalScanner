from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.hotpost_clues import CardType
from app.schemas.hotpost_signal import SourceScopeId


class DraftGroupSeedRequest(ORMModel):
    candidate_ids: list[str] = Field(min_length=2)
    card_type: CardType


class SuggestionDraftSeedRequest(ORMModel):
    suggestion_id: str
    card_type: CardType


class BreakdownSuggestion(ORMModel):
    suggestion_id: str
    source_scope_id: SourceScopeId
    topic_pack_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    thread_count: int
    community_count: int
    intent_tags: list[str] = Field(default_factory=list)
    evidence_score: int
    hypothesis: str
    reason_codes: list[str] = Field(default_factory=list)


class BreakdownSuggestionListResponse(ORMModel):
    items: list[BreakdownSuggestion] = Field(default_factory=list)


class BreakdownDraftMaterializeResult(ORMModel):
    suggestion_id: str
    status: str
    draft_id: str
    card_id: str
    reason:Optional[ str] = None


class BreakdownDraftMaterializeResponse(ORMModel):
    items: list[BreakdownDraftMaterializeResult] = Field(default_factory=list)


__all__ = [
    "BreakdownDraftMaterializeResponse",
    "BreakdownDraftMaterializeResult",
    "BreakdownSuggestion",
    "BreakdownSuggestionListResponse",
    "DraftGroupSeedRequest",
    "SuggestionDraftSeedRequest",
]
