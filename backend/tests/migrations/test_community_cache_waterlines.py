from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_community_cache_has_backfill_and_attempt_columns() -> None:
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='community_cache'
                  AND column_name IN (
                        'backfill_floor',
                        'last_attempt_at',
                        'backfill_status',
                        'coverage_months',
                        'sample_posts',
                        'sample_comments',
                        'backfill_capped',
                        'backfill_cursor',
                        'backfill_cursor_created_at',
                        'backfill_updated_at'
                  )
                """
            )
        )
        cols = {r[0] for r in rows.all()}
        assert cols == {
            "backfill_floor",
            "last_attempt_at",
            "backfill_status",
            "coverage_months",
            "sample_posts",
            "sample_comments",
            "backfill_capped",
            "backfill_cursor",
            "backfill_cursor_created_at",
            "backfill_updated_at",
        }
