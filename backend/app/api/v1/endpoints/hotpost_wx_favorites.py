from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mini_auth import decode_mini_jwt_token
from app.core.security import TokenPayload
from app.db.session import get_session
from app.schemas.hotpost_wx_favorites import FavoriteBatchRequest, FavoriteCardListResponse, FavoriteMutationResponse
from app.services.hotpost.mini_favorite_service import add_favorite, batch_add_favorites, list_favorites, remove_favorite


router = APIRouter(prefix="/hotpost/wx-favorites", tags=["hotpost-mini"])


@router.post("/batch", response_model=FavoriteMutationResponse)
async def wx_batch_add_favorites(
    payload: FavoriteBatchRequest,
    token: TokenPayload = Depends(decode_mini_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> FavoriteMutationResponse:
    imported = await batch_add_favorites(db, token.sub, payload.card_ids)
    return FavoriteMutationResponse(imported_count=imported)


@router.get("", response_model=FavoriteCardListResponse)
async def wx_list_favorites(
    token: TokenPayload = Depends(decode_mini_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> FavoriteCardListResponse:
    return FavoriteCardListResponse(items=await list_favorites(db, token.sub))


@router.post("/{card_id}", response_model=FavoriteMutationResponse)
async def wx_add_favorite(
    card_id: str,
    token: TokenPayload = Depends(decode_mini_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> FavoriteMutationResponse:
    await add_favorite(db, token.sub, card_id)
    return FavoriteMutationResponse()


@router.delete("/{card_id}", response_model=FavoriteMutationResponse)
async def wx_remove_favorite(
    card_id: str,
    token: TokenPayload = Depends(decode_mini_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> FavoriteMutationResponse:
    await remove_favorite(db, token.sub, card_id)
    return FavoriteMutationResponse()


__all__ = ["router"]
