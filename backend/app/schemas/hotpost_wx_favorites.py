from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.hotpost_clues import CardSummary


class FavoriteCardSummary(CardSummary):
    favorited_at: datetime


class FavoriteCardListResponse(ORMModel):
    items: list[FavoriteCardSummary] = Field(default_factory=list)


class FavoriteBatchRequest(ORMModel):
    card_ids: list[str] = Field(default_factory=list)


class FavoriteMutationResponse(ORMModel):
    ok: bool = True
    imported_count: int = 0


__all__ = [
    "FavoriteBatchRequest",
    "FavoriteCardListResponse",
    "FavoriteCardSummary",
    "FavoriteMutationResponse",
]
