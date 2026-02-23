from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_insert_comment_minimal_fields() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        await session.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id, source, source_post_id, subreddit,
                    depth, body, created_utc, score
                ) VALUES (
                    :cid, 'reddit', :pid, :sub, 0, :body, :ts, 1
                )
                """
            ),
            {
                "cid": "t1_testcid",
                "pid": "t3_testpost",
                "sub": "r/test",
                "body": "hello world",
                "ts": now,
            },
        )

        # verify persisted
        row = await session.execute(
            text("SELECT count(*) FROM comments WHERE reddit_comment_id=:cid"),
            {"cid": "t1_testcid"},
        )
        assert row.scalar() == 1


@pytest.mark.asyncio
async def test_unique_reddit_comment_id_enforced() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        # insert first
        await session.execute(
            text(
                """
                INSERT INTO comments (reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc)
                VALUES (:cid, 'reddit', :pid, :sub, 0, :body, :ts)
                """
            ),
            {
                "cid": "t1_dup",
                "pid": "t3_post",
                "sub": "r/test",
                "body": "first",
                "ts": now,
            },
        )
        # attempt duplicate
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    """
                    INSERT INTO comments (reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc)
                    VALUES (:cid, 'reddit', :pid, :sub, 0, :body, :ts)
                    """
                ),
                {
                    "cid": "t1_dup",
                    "pid": "t3_post2",
                    "sub": "r/test",
                    "body": "second",
                    "ts": now,
                },
            )
