from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.infrastructure.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_probe_hot_writes_evidence_posts_and_candidates_with_caps_and_is_idempotent() -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    seed = uuid.uuid4().hex[:8]
    now_epoch = datetime.now(timezone.utc).timestamp()

    hot_sources = [
        {"subreddit": "r/all", "sort": "rising", "time_filter": "day"},
        {"subreddit": "r/all", "sort": "top", "time_filter": "day"},
    ]

    def make_post(*, i: int, subreddit: str) -> RedditPost:
        return RedditPost(
            id=f"hot_{seed}_{i}",
            title=f"title {i}",
            selftext="...",
            score=200 - i,  # satisfy default min_score
            num_comments=0,
            created_utc=now_epoch,
            subreddit=subreddit,
            author="a",
            url="u",
            permalink="p",
        )

    # 5 subreddits -> will be truncated to top 3 candidates
    feed_posts = []
    for idx, sub in enumerate(["s1", "s2", "s3", "s4", "s5"]):
        # 3 posts each, but per-subreddit cap is 2 -> should truncate within each
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
            "hot_sources": hot_sources,
            "max_candidate_subreddits": 3,
            "max_evidence_per_subreddit": 2,
            "max_age_hours": 72,
        },
    )

    crawl_run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())

    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id, config={"mode": "test_probe_hot"})
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:hot",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="test",
            idempotency_key_human="test",
            config=plan.model_dump(mode="json"),
        )

        out1 = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=cast(AsyncSession, session),
            reddit_client=cast(Any, DummyRedditClient()),
            crawl_run_id=crawl_run_id,
            community_run_id=target_id,
        )
        await session.commit()

    assert out1.get("plan_kind") == "probe"
    assert out1.get("source") == "hot"
    assert out1.get("status") == "partial"
    assert out1.get("reason") == "caps_reached"
    assert out1.get("discovered_communities_upserted") == 3
    assert out1.get("evidence_posts_written") == 6  # 3 candidates × 2 evidence

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT subreddit, count(*)
                FROM evidence_posts
                WHERE probe_source='hot'
                  AND source_post_id LIKE :prefix
                GROUP BY subreddit
                ORDER BY subreddit
                """
            ),
            {"prefix": f"hot_{seed}_%"},
        )
        per_sub = dict(rows.all())

    assert max(per_sub.values()) <= 2
    assert sum(per_sub.values()) == 6

    # Rerun with a different run_id/target_id: evidence_posts should not grow (same query_hash+post_ids).
    async with SessionFactory() as session:
        new_run = str(uuid.uuid4())
        new_target = str(uuid.uuid4())
        await ensure_crawler_run(session, crawl_run_id=new_run, config={"mode": "test_probe_hot"})
        await ensure_crawler_run_target(
            session,
            community_run_id=new_target,
            crawl_run_id=new_run,
            subreddit="probe:hot",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="test2",
            idempotency_key_human="test2",
            config=plan.model_dump(mode="json"),
        )
        out2 = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=cast(AsyncSession, session),
            reddit_client=cast(Any, DummyRedditClient()),
            crawl_run_id=new_run,
            community_run_id=new_target,
        )
        await session.commit()

    assert out2.get("evidence_posts_written") == 0
