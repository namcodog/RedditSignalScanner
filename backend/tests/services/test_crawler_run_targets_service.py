from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    ensure_crawler_run_target,
    fail_crawler_run_target,
)


@pytest.mark.asyncio
async def test_crawler_run_targets_lifecycle() -> None:
    crawl_run_id = str(uuid.uuid4())
    community_run_id = str(uuid.uuid4())
    subreddit = "test"

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=community_run_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            config={"tier": "seed"},
        )
        await session.commit()

        row = await session.execute(
            text(
                """
                SELECT crawl_run_id, subreddit, status
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": community_run_id},
        )
        crawl_run_id_db, subreddit_db, status_db = row.one()
        assert str(crawl_run_id_db) == crawl_run_id
        assert str(subreddit_db) == subreddit
        assert str(status_db) == "running"

        await complete_crawler_run_target(
            session, community_run_id=community_run_id, metrics={"new_posts": 1}
        )
        await session.commit()

        done = await session.execute(
            text(
                """
                SELECT status, metrics->>'new_posts'
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": community_run_id},
        )
        status_done, new_posts = done.one()
        assert status_done == "completed"
        assert new_posts == "1"

        await fail_crawler_run_target(
            session,
            community_run_id=community_run_id,
            error_message_short="boom",
        )
        await session.commit()

        failed = await session.execute(
            text(
                """
                SELECT status, error_message_short
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": community_run_id},
        )
        status_failed, msg = failed.one()
        assert status_failed == "failed"
        assert msg == "boom"

