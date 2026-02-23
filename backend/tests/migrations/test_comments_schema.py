from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_comments_table_exists_and_indexes() -> None:
    async with SessionFactory() as session:
        # table exists
        tbl = await session.execute(
            text(
                """
                SELECT to_regclass('public.comments') IS NOT NULL
                """
            )
        )
        assert tbl.scalar() is True

        # unique index/constraint on reddit_comment_id exists via constraint name
        uq = await session.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conname = 'uq_comments_reddit_comment_id'
                """
            )
        )
        assert uq.scalar() == "uq_comments_reddit_comment_id"

        # time-based indexes exist
        idx1 = await session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename='comments' AND indexname='idx_comments_post_time'
                """
            )
        )
        assert idx1.scalar() is not None

        idx2 = await session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename='comments' AND indexname='idx_comments_subreddit_time'
                """
            )
        )
        assert idx2.scalar() is not None


@pytest.mark.asyncio
async def test_semantic_tables_exist() -> None:
    async with SessionFactory() as session:
        for table in ("content_labels", "content_entities"):
            cur = await session.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f"public.{table}"})
            assert cur.scalar() is True, f"{table} should exist"

