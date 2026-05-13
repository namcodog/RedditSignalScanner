from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.schemas.hotpost_clues import CardEventRequest, CardEventResponse, CardListResponse, CardListType, CategoryListResponse, ValidationCardDetail, WritingCardDetail
from app.services.hotpost.hotpost_supply_contract import get_supply_operation_defaults
from app.services.hotpost.mini_surface_contract import get_mini_supplement_surface_rules
from app.services.hotpost.clues_catalog import get_card_detail, list_card_summaries, list_categories
from app.services.hotpost.clues_state import record_event


router = APIRouter(prefix="/hotpost", tags=["hotpost"])


@router.get("/categories", response_model=CategoryListResponse)
async def hotpost_categories() -> CategoryListResponse:
    return CategoryListResponse(items=list_categories())


@router.get("/cards", response_model=CardListResponse)
async def hotpost_cards(
    card_type: CardListType = Query(default="all"),
    cursor:Optional[ str] = Query(default=None),
    page_size:Optional[ int] = Query(default=None, ge=1),
) -> CardListResponse:
    if card_type == "supplement":
        supplement_rules = get_mini_supplement_surface_rules()
        resolved_page_size = int(page_size or supplement_rules["initial_page_size"])
        max_page_size = int(supplement_rules["max_page_size"])
    else:
        operation_defaults = get_supply_operation_defaults()
        resolved_page_size = int(page_size or operation_defaults["feed_initial_page_size"])
        max_page_size = int(operation_defaults["feed_max_page_size"])
    if resolved_page_size > max_page_size:
        raise HTTPException(status_code=422, detail=f"page_size must be <= {max_page_size}")
    items, next_cursor = list_card_summaries(
        card_type=card_type,
        cursor=cursor,
        page_size=resolved_page_size,
    )
    return CardListResponse(items=items, next_cursor=next_cursor)


@router.get("/cards/{card_id}", response_model=ValidationCardDetail | WritingCardDetail)
async def hotpost_card_detail(card_id: str) -> ValidationCardDetail | WritingCardDetail:
    detail = get_card_detail(card_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return detail


@router.post("/card-events", response_model=CardEventResponse)
async def hotpost_card_event(payload: CardEventRequest, settings: Settings = Depends(get_settings)) -> CardEventResponse:
    if payload.card_id and get_card_detail(payload.card_id) is None:
        raise HTTPException(status_code=404, detail="Card not found")
    if payload.category_id and payload.category_id != "all":
        known = {item.category_id for item in list_categories()}
        if payload.category_id not in known:
            raise HTTPException(status_code=404, detail="Category not found")
    redis = Redis.from_url(settings.reddit_cache_redis_url, decode_responses=True)
    try:
        await record_event(redis, event_type=payload.type, card_id=payload.card_id, category_id=payload.category_id)
        return CardEventResponse()
    finally:
        await redis.close()
