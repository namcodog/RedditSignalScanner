from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_community_cache_has_trigram_index() -> None:
    async with SessionFactory() as session:
        result = await session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'community_cache'
                AND indexname = 'idx_community_cache_name_trgm'
                """
            )
        )
        assert result.scalar() is not None
