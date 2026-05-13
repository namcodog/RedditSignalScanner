from __future__ import annotations

from fastapi import APIRouter

from app.schemas.hotpost_card_candidates import CandidateListResponse
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.source_scope_candidate_collector import collect_scope_candidates


router = APIRouter(prefix="/hotpost/source-scopes", tags=["hotpost"])


@router.post("/{scope_id}/collect-candidates", response_model=CandidateListResponse)
async def hotpost_collect_scope_candidates(scope_id: SourceScopeId) -> CandidateListResponse:
    return CandidateListResponse(items=await collect_scope_candidates(scope_id))
