from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.hotpost_clues import CardType
from app.schemas.hotpost_card_drafts import DraftImportRequest, DraftListResponse, DraftPublishResponse
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.card_draft_store import list_drafts, publish_draft, save_draft, update_draft


router = APIRouter(prefix="/hotpost/card-drafts", tags=["hotpost"])


@router.get("", response_model=DraftListResponse)
async def hotpost_card_drafts(
    source_scope_id:Optional[ SourceScopeId] = None,
    card_type:Optional[ CardType] = None,
) -> DraftListResponse:
    return DraftListResponse(items=list_drafts(source_scope_id, card_type))


@router.post("", response_model=DraftListResponse)
async def hotpost_import_card_draft(payload: DraftImportRequest) -> DraftListResponse:
    try:
        save_draft(payload.card)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftListResponse(items=list_drafts())


@router.put("/{draft_id}", response_model=DraftListResponse)
async def hotpost_update_card_draft(draft_id: str, payload: DraftImportRequest) -> DraftListResponse:
    try:
        update_draft(draft_id, payload.card)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftListResponse(items=list_drafts())


@router.post("/{draft_id}/publish", response_model=DraftPublishResponse)
async def hotpost_publish_card_draft(draft_id: str) -> DraftPublishResponse:
    try:
        card_id, published_count = publish_draft(draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DraftPublishResponse(card_id=card_id, published_count=published_count)
