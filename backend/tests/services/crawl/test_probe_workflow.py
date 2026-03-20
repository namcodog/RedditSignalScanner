from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits
from app.services.crawl.probe_workflow import (
    ProbeWorkflowDeps,
    ProbeWorkflowInput,
    execute_probe_workflow,
)
from app.services.infrastructure.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_probe_workflow_search_writes_evidence_and_candidates() -> None:
    seed = uuid.uuid4().hex[:8]
    query = f"payment dispute {seed}"
    now_epoch = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    sub_a = f"shop_{seed}"
    sub_b = f"stripe_{seed}"
    sub_a_key = f"r/{sub_a.lower()}"
    sub_b_key = f"r/{sub_b.lower()}"

    posts = [
        RedditPost(
            id=f"p1_{seed}",
            title="Refund issue",
            selftext="context",
            score=10,
            num_comments=3,
            created_utc=now_epoch,
            subreddit=sub_a,
            author="a1",
            url="u",
            permalink="p",
        ),
        RedditPost(
            id=f"p2_{seed}",
            title="Chargeback issue",
            selftext="context",
            score=5,
            num_comments=10,
            created_utc=now_epoch,
            subreddit=sub_a,
            author="a2",
            url="u",
            permalink="p",
        ),
        RedditPost(
            id=f"p3_{seed}",
            title="Stripe payout delay",
            selftext="context",
            score=8,
            num_comments=1,
            created_utc=now_epoch,
            subreddit=sub_b,
            author="a3",
            url="u",
            permalink="p",
        ),
    ]

    class DummyRedditClient:
        async def search_posts(self, *_: Any, **__: Any) -> list[RedditPost]:
            return list(posts)

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="query",
        target_value=query,
        reason="user_query",
        limits=CrawlPlanLimits(posts_limit=10),
        meta={"source": "search", "time_filter": "week", "sort": "relevance"},
    )

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id, config={"mode": "test_probe"})
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:test",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="probe",
            idempotency_key_human="probe",
            config=plan.model_dump(mode="json"),
        )
        out = await execute_probe_workflow(
            workflow_input=ProbeWorkflowInput(
                plan=plan,
                session=cast(AsyncSession, session),
                reddit_client=cast(Any, DummyRedditClient()),
                crawl_run_id=crawl_run_id,
                community_run_id=target_id,
            ),
            deps=ProbeWorkflowDeps(),
        )
        await session.commit()

    assert out.payload["status"] == "completed"
    assert out.payload["evidence_posts_written"] == 3
    assert out.payload["discovered_communities_upserted"] == 2

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT name, discovered_count
                FROM discovered_communities
                WHERE name IN (:a, :b)
                ORDER BY name
                """
            ),
            {"a": sub_a_key, "b": sub_b_key},
        )
        assert rows.all() == [(sub_a_key, 2), (sub_b_key, 1)]


@pytest.mark.asyncio
async def test_probe_workflow_hot_marks_partial_when_caps_reached() -> None:
    seed = uuid.uuid4().hex[:8]
    now_epoch = datetime.now(timezone.utc).timestamp()

    def make_post(*, i: int, subreddit: str) -> RedditPost:
        return RedditPost(
            id=f"hot_{seed}_{i}",
            title=f"title {i}",
            selftext="...",
            score=200 - i,
            num_comments=0,
            created_utc=now_epoch,
            subreddit=subreddit,
            author="a",
            url="u",
            permalink="p",
        )

    feed_posts: list[RedditPost] = []
    for idx, sub in enumerate(["s1", "s2", "s3", "s4", "s5"]):
        feed_posts.extend([make_post(i=idx * 10 + j, subreddit=sub) for j in range(3)])

    class DummyRedditClient:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            return list(feed_posts), None

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="subreddit",
        target_value=f"r/probe_hot_{seed}",
        reason="hot_probe",
        limits=CrawlPlanLimits(posts_limit=25),
        meta={
            "source": "hot",
            "hot_sources": [
                {"subreddit": "r/all", "sort": "rising", "time_filter": "day"},
                {"subreddit": "r/all", "sort": "top", "time_filter": "day"},
            ],
            "max_candidate_subreddits": 3,
            "max_evidence_per_subreddit": 2,
            "max_age_hours": 72,
        },
    )

    async with SessionFactory() as session:
        crawl_run_id = str(uuid.uuid4())
        target_id = str(uuid.uuid4())
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "test_probe_hot_workflow"},
        )
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:hot",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="probe_hot_workflow",
            idempotency_key_human="probe_hot_workflow",
            config=plan.model_dump(mode="json"),
        )
        out = await execute_probe_workflow(
            workflow_input=ProbeWorkflowInput(
                plan=plan,
                session=cast(AsyncSession, session),
                reddit_client=cast(Any, DummyRedditClient()),
                crawl_run_id=crawl_run_id,
                community_run_id=target_id,
            ),
            deps=ProbeWorkflowDeps(),
        )

    assert out.payload["status"] == "partial"
    assert out.payload["reason"] == "caps_reached"
    assert out.payload["discovered_communities_upserted"] == 3
    assert out.payload["evidence_posts_written"] == 6
