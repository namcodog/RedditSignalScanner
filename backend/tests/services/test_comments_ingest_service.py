from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.comments_ingest import persist_comments


@pytest.mark.asyncio
async def test_persist_comments_idempotent() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        items = [
            {
                "id": "t1_abc",
                "body": "Great point about subscription fees.",
                "created_utc": int(now.timestamp()),
                "depth": 0,
                "score": 5,
                "author": "u_test",
            }
        ]

        n1 = await persist_comments(
            session,
            source_post_id="t3_post123",
            subreddit="r/homegym",
            comments=items,
        )
        n2 = await persist_comments(
            session,
            source_post_id="t3_post123",
            subreddit="r/homegym",
            comments=items,
        )

        assert n1 == 1 and n2 == 1

        await session.commit()

        count = await session.execute(
            text("SELECT count(*) FROM comments WHERE reddit_comment_id='t1_abc'")
        )
        assert count.scalar() == 1

        author_row = await session.execute(
            text("SELECT 1 FROM authors WHERE author_id = :aid"),
            {"aid": "u_test"},
        )
        assert author_row.scalar_one_or_none() == 1


@pytest.mark.asyncio
async def test_persist_comments_writes_crawl_run_id_when_supported() -> None:
    async with SessionFactory() as session:
        run_id = str(uuid.uuid4())
        community_run_id = str(uuid.uuid4())
        source_post_id = f"t3_runid_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        # Ensure a matching posts_raw row exists (persist_comments resolves post_id).
        await session.execute(
            text(
                """
                INSERT INTO posts_raw (source, source_post_id, version, created_at, fetched_at, valid_from, subreddit, title, body, is_current)
                VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true)
                """
            ),
            {"pid": source_post_id, "ts": now},
        )
        await session.commit()

        items = [
            {
                "id": f"t1_runid_{uuid.uuid4().hex[:8]}",
                "body": "hello",
                "created_utc": int(now.timestamp()),
                "depth": 0,
                "score": 1,
                "author": "u_test",
            }
        ]

        n = await persist_comments(
            session,
            source_post_id=source_post_id,
            subreddit="r/test",
            comments=items,
            crawl_run_id=run_id,
            community_run_id=community_run_id,
        )
        assert n == 1
        await session.commit()

        row = await session.execute(
            text(
                """
                SELECT c.crawl_run_id, c.community_run_id
                FROM comments c
                WHERE c.reddit_comment_id = :cid
                """
            ),
            {"cid": str(items[0]["id"])},
        )
        crawl_run_id, stored_community_run_id = row.one()
        assert str(crawl_run_id) == run_id
        assert str(stored_community_run_id) == community_run_id

        # FK should be satisfied: crawler_runs row exists for the run_id (best-effort).
        run_row = await session.execute(
            text("SELECT 1 FROM crawler_runs WHERE id = CAST(:id AS uuid)"),
            {"id": run_id},
        )
        assert run_row.scalar_one_or_none() == 1
