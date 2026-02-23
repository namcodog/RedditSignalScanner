from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.services.crawler_runs_service import ensure_crawler_run


@pytest.mark.asyncio
async def test_crawler_run_targets_allows_multiple_plans_per_subreddit() -> None:
    crawl_run_id = str(uuid.uuid4())
    subreddit = "r/test"

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id)
        await session.commit()

        plan_id_1 = str(uuid.uuid4())
        plan_id_2 = str(uuid.uuid4())
        await session.execute(
            text(
                """
                INSERT INTO crawler_run_targets (
                    id, crawl_run_id, subreddit, status, config, metrics,
                    idempotency_key, idempotency_key_human, plan_kind
                ) VALUES (
                    CAST(:id1 AS uuid), CAST(:run AS uuid), :sub, 'running',
                    '{}'::jsonb, '{}'::jsonb, :k1, :h1, :kind
                ), (
                    CAST(:id2 AS uuid), CAST(:run AS uuid), :sub, 'running',
                    '{}'::jsonb, '{}'::jsonb, :k2, :h2, :kind
                )
                """
            ),
            {
                "id1": plan_id_1,
                "id2": plan_id_2,
                "run": crawl_run_id,
                "sub": subreddit,
                "k1": "k1",
                "k2": "k2",
                "h1": "subreddit:r/test|patrol",
                "h2": "subreddit:r/test|patrol|2",
                "kind": "patrol",
            },
        )
        await session.commit()

        # Same crawl_run_id + same idempotency_key must be unique (plan identity).
        dup_plan_id = str(uuid.uuid4())
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    """
                    INSERT INTO crawler_run_targets (
                        id, crawl_run_id, subreddit, status, config, metrics,
                        idempotency_key, idempotency_key_human, plan_kind
                    ) VALUES (
                        CAST(:id AS uuid), CAST(:run AS uuid), :sub, 'running',
                        '{}'::jsonb, '{}'::jsonb, :k, :h, :kind
                    )
                    """
                ),
                {
                    "id": dup_plan_id,
                    "run": crawl_run_id,
                    "sub": subreddit,
                    "k": "k1",
                    "h": "subreddit:r/test|patrol|dup",
                    "kind": "patrol",
                },
            )
            await session.commit()
        await session.rollback()

