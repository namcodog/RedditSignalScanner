from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.hotpost_card_drafts import DraftListResponse
from app.schemas.hotpost_card_review import (
    BreakdownDraftMaterializeResponse,
    BreakdownSuggestionListResponse,
    DraftGroupSeedRequest,
    SuggestionDraftSeedRequest,
)
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.breakdown_candidate_clusterer import get_breakdown_suggestion, list_breakdown_suggestions
from app.services.hotpost.breakdown_draft_materializer import materialize_breakdown_drafts
from app.services.hotpost.card_candidate_store import get_candidates
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_draft_store import list_drafts, save_draft
from app.services.hotpost.card_group_draft_builder import seed_group_validation_draft, seed_group_writing_draft


router = APIRouter(prefix="/hotpost/card-review", tags=["hotpost"])


@router.get("/suggestions", response_model=BreakdownSuggestionListResponse)
async def hotpost_breakdown_suggestions(
    source_scope_id:Optional[ SourceScopeId] = None,
    limit: int = 20,
) -> BreakdownSuggestionListResponse:
    return BreakdownSuggestionListResponse(items=list_breakdown_suggestions(source_scope_id, limit=limit))


@router.post("/materialize-drafts", response_model=BreakdownDraftMaterializeResponse)
async def hotpost_materialize_breakdown_drafts(
    source_scope_id:Optional[ SourceScopeId] = None,
    limit: int = 20,
) -> BreakdownDraftMaterializeResponse:
    return BreakdownDraftMaterializeResponse(items=await materialize_breakdown_drafts(source_scope_id, limit=limit))


@router.post("/seed-draft", response_model=DraftListResponse)
async def hotpost_seed_group_draft(payload: DraftGroupSeedRequest) -> DraftListResponse:
    try:
        candidates = get_candidates(payload.candidate_ids)
        await _save_generated_group_draft(candidates, payload.card_type)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftListResponse(items=list_drafts())


@router.post("/seed-draft-from-suggestion", response_model=DraftListResponse)
async def hotpost_seed_group_draft_from_suggestion(payload: SuggestionDraftSeedRequest) -> DraftListResponse:
    try:
        suggestion = get_breakdown_suggestion(payload.suggestion_id)
        candidates = get_candidates(suggestion.candidate_ids)
        await _save_generated_group_draft(candidates, payload.card_type)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftListResponse(items=list_drafts())


async def _save_generated_group_draft(candidates, card_type):
    draft = seed_group_validation_draft(candidates) if card_type == "validate" else seed_group_writing_draft(candidates)
    draft = await generate_card_content(draft)
    if card_type == "write" and draft.card_type != "write":
        raise ValueError("Suggestion does not meet breakdown threshold yet")
    save_draft(draft)
