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
async def test_probe_search_writes_evidence_posts_and_upserts_discovered_communities_idempotently() -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    seed = uuid.uuid4().hex[:8]
    query = f"shopify refund {seed}"
    now_epoch = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    sub_shopify = f"Shopify_{seed}"
    sub_stripe = f"stripe_{seed}"
    shopify_key = f"r/{sub_shopify.lower()}"
    stripe_key = f"r/{sub_stripe.lower()}"

    posts = [
        RedditPost(
            id=f"p1_{seed}",
            title="Refund policy help",
            selftext="...",
            score=10,
            num_comments=3,
            created_utc=now_epoch,
            subreddit=sub_shopify,
            author="a1",
            url="u",
            permalink="p",
        ),
        RedditPost(
            id=f"p2_{seed}",
            title="Chargeback issue",
            selftext="...",
            score=5,
            num_comments=10,
            created_utc=now_epoch,
            subreddit=sub_shopify,
            author="a2",
            url="u",
            permalink="p",
        ),
        RedditPost(
            id=f"p3_{seed}",
            title="Stripe payout delay",
            selftext="...",
            score=8,
            num_comments=1,
            created_utc=now_epoch,
            subreddit=sub_stripe,
            author="a3",
            url="u",
            permalink="p",
        ),
        # duplicate post id (should be deduped by evidence_posts unique key)
        RedditPost(
            id=f"p3_{seed}",
            title="Stripe payout delay",
            selftext="...",
            score=8,
            num_comments=1,
            created_utc=now_epoch,
            subreddit=sub_stripe,
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
    assert out1.get("source") == "search"

    async with SessionFactory() as session:
        row = await session.execute(
            text("SELECT count(*) FROM evidence_posts WHERE source_query = :q"),
            {"q": query},
        )
        (count_1,) = row.one()
        assert int(count_1) == 3

        rows = await session.execute(
            text(
                """
                SELECT name, discovered_count, status
                FROM discovered_communities
                WHERE name IN (:a, :b)
                ORDER BY name
                """
            ),
            {"a": shopify_key, "b": stripe_key},
        )
        records_1 = rows.all()
        assert records_1 == [
            (shopify_key, 2, "pending"),
            (stripe_key, 1, "pending"),
        ]

    # Run again with the same query/posts: evidence_posts should not grow, discovered_count should not inflate.
    async with SessionFactory() as session:
        new_run = str(uuid.uuid4())
        new_target = str(uuid.uuid4())
        await ensure_crawler_run(session, crawl_run_id=new_run, config={"mode": "test_probe"})
        await ensure_crawler_run_target(
            session,
            community_run_id=new_target,
            crawl_run_id=new_run,
            subreddit="probe:test",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="test2",
            idempotency_key_human="test2",
            config=plan.model_dump(mode="json"),
        )
        await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=cast(AsyncSession, session),
            reddit_client=cast(Any, DummyRedditClient()),
            crawl_run_id=new_run,
            community_run_id=new_target,
        )
        await session.commit()

    async with SessionFactory() as session:
        row = await session.execute(
            text("SELECT count(*) FROM evidence_posts WHERE source_query = :q"),
            {"q": query},
        )
        (count_2,) = row.one()
        assert int(count_2) == 3

        rows = await session.execute(
            text(
                """
                SELECT name, discovered_count, status
                FROM discovered_communities
                WHERE name IN (:a, :b)
                ORDER BY name
                """
            ),
            {"a": shopify_key, "b": stripe_key},
        )
        records_2 = rows.all()
        assert records_2 == records_1


@pytest.mark.asyncio
async def test_probe_search_enforces_evidence_and_discovery_caps_and_marks_partial() -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    seed = uuid.uuid4().hex[:8]
    query = f"big query {seed}"
    now_epoch = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc).timestamp()

    posts = []
    for i in range(20):
        posts.append(
            RedditPost(
                id=f"p{i}_{seed}",
                title=f"t{i}",
                selftext="...",
                score=100 - i,
                num_comments=0,
                created_utc=now_epoch,
                subreddit=f"s{i}_{seed}",
                author="a",
                url="u",
                permalink="p",
            )
        )

    class DummyRedditClient:
        async def search_posts(self, *_: Any, **__: Any) -> list[RedditPost]:
            return list(posts)

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="query",
        target_value=query,
        reason="user_query",
        limits=CrawlPlanLimits(posts_limit=20),
        meta={
            "source": "search",
            "time_filter": "week",
            "sort": "relevance",
            "max_evidence_posts": 10,
            "max_discovered_communities": 5,
        },
    )

    async with SessionFactory() as session:
        crawl_run_id = str(uuid.uuid4())
        target_id = str(uuid.uuid4())
        await ensure_crawler_run(session, crawl_run_id=crawl_run_id, config={"mode": "test_probe"})
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe:test",
            status="running",
            plan_kind=plan.plan_kind,
            idempotency_key="test_caps",
            idempotency_key_human="test_caps",
            config=plan.model_dump(mode="json"),
        )
        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=cast(AsyncSession, session),
            reddit_client=cast(Any, DummyRedditClient()),
            crawl_run_id=crawl_run_id,
            community_run_id=target_id,
        )
        await session.commit()

    assert out.get("status") == "partial"
    assert out.get("reason") == "caps_reached"
    assert out.get("evidence_posts_written") == 10
    assert out.get("discovered_communities_upserted") == 5
