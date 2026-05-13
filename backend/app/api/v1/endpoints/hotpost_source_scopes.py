from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.hotpost_signal import SourceScopeId
from app.schemas.hotpost_source_scopes import RedditSearchSpecListResponse, SourceScopeListResponse
from app.services.hotpost.reddit_search_spec_builder import build_reddit_search_specs
from app.services.hotpost.source_scope_catalog import list_source_scopes


router = APIRouter(prefix="/hotpost/source-scopes", tags=["hotpost"])


@router.get("", response_model=SourceScopeListResponse)
async def hotpost_source_scopes() -> SourceScopeListResponse:
    return SourceScopeListResponse(items=list_source_scopes())


@router.get("/{scope_id}/search-specs", response_model=RedditSearchSpecListResponse)
async def hotpost_source_scope_specs(scope_id: SourceScopeId) -> RedditSearchSpecListResponse:
    try:
        return RedditSearchSpecListResponse(items=build_reddit_search_specs(scope_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source scope not found") from exc
