from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mini_user import MiniUserFavorite
from app.schemas.hotpost_wx_favorites import FavoriteCardSummary
from app.services.hotpost.clues_catalog import get_card_summary, list_card_summaries_by_ids


async def list_favorites(db: AsyncSession, user_id: str) -> list[FavoriteCardSummary]:
    user_uuid = uuid.UUID(user_id)
    rows = (
        await db.execute(
            select(MiniUserFavorite).where(MiniUserFavorite.user_id == user_uuid).order_by(MiniUserFavorite.created_at.desc())
        )
    ).scalars().all()
    summaries = {item.card_id: item for item in list_card_summaries_by_ids([row.card_id for row in rows])}
    return [
        FavoriteCardSummary.model_validate({**summaries[row.card_id].model_dump(), "favorited_at": row.created_at})
        for row in rows
        if row.card_id in summaries
    ]


async def add_favorite(db: AsyncSession, user_id: str, card_id: str) -> None:
    user_uuid = uuid.UUID(user_id)
    if get_card_summary(card_id) is None:
        return
    exists = await db.scalar(select(MiniUserFavorite).where(MiniUserFavorite.user_id == user_uuid, MiniUserFavorite.card_id == card_id))
    if exists is None:
        db.add(MiniUserFavorite(user_id=user_uuid, card_id=card_id))
        await db.commit()


async def remove_favorite(db: AsyncSession, user_id: str, card_id: str) -> None:
    await db.execute(delete(MiniUserFavorite).where(MiniUserFavorite.user_id == uuid.UUID(user_id), MiniUserFavorite.card_id == card_id))
    await db.commit()


async def batch_add_favorites(db: AsyncSession, user_id: str, card_ids: list[str]) -> int:
    user_uuid = uuid.UUID(user_id)
    valid_ids = [card_id for card_id in dict.fromkeys(card_ids) if get_card_summary(card_id) is not None]
    existing = set(
        (
            await db.execute(
                select(MiniUserFavorite.card_id).where(MiniUserFavorite.user_id == user_uuid, MiniUserFavorite.card_id.in_(valid_ids))
            )
        ).scalars()
    )
    rows = [MiniUserFavorite(user_id=user_uuid, card_id=card_id) for card_id in valid_ids if card_id not in existing]
    db.add_all(rows)
    if rows:
        await db.commit()
    return len(rows)


__all__ = ["add_favorite", "batch_add_favorites", "list_favorites", "remove_favorite"]
