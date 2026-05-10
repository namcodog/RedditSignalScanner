from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.hotpost_card_candidates import CandidateImportRequest, CandidateListResponse
from app.schemas.hotpost_card_drafts import DraftListResponse, DraftSeedRequest
from app.schemas.hotpost_signal import SignalLevel, SourceScopeId
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_candidate_store import get_candidate, list_candidates, save_candidate
from app.services.hotpost.card_draft_builder import seed_validation_draft, seed_writing_draft
from app.services.hotpost.card_draft_store import list_drafts, save_draft


router = APIRouter(prefix="/hotpost/card-candidates", tags=["hotpost"])


@router.get("", response_model=CandidateListResponse)
async def hotpost_card_candidates(
    source_scope_id:Optional[ SourceScopeId] = None,
    signal_level:Optional[ SignalLevel] = None,
) -> CandidateListResponse:
    return CandidateListResponse(items=list_candidates(source_scope_id, signal_level))


@router.post("", response_model=CandidateListResponse)
async def hotpost_import_card_candidate(payload: CandidateImportRequest) -> CandidateListResponse:
    try:
        save_candidate(payload.candidate)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CandidateListResponse(items=list_candidates())


@router.post("/{candidate_id}/seed-draft", response_model=DraftListResponse)
async def hotpost_seed_candidate_draft(candidate_id: str, payload: DraftSeedRequest) -> DraftListResponse:
    try:
        candidate = get_candidate(candidate_id)
        draft = seed_validation_draft(candidate) if payload.card_type == "validate" else seed_writing_draft(candidate)
        draft = await generate_card_content(draft)
        save_draft(draft)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftListResponse(items=list_drafts())
