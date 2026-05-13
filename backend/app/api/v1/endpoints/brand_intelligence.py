from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.brand_intelligence.brand_registry_reader import (
    read_brand_registry_view,
)

router = APIRouter(prefix="/brand-intelligence", tags=["brand-intelligence"])


async def brand_registry_view(
    status: str | None = Query(default=None),
    interest_tag: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await read_brand_registry_view(
        db,
        status_filter=status,
        interest_tag_filter=interest_tag,
        limit=limit,
        consumer_profile_id="consumer_safe",
    )


router.add_api_route(
    "/registry",
    brand_registry_view,
    methods=["GET"],
)
