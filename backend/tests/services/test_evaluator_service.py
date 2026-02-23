from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from app.models.discovered_community import DiscoveredCommunity
from app.services.discovery.evaluator_service import CommunityEvaluator


@pytest.mark.asyncio
async def test_fetch_sample_posts_from_db_accepts_int_days(db_session) -> None:
    await db_session.execute(text("DELETE FROM posts_raw WHERE source_post_id = 't3_eval'"))
    await db_session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/testeval'"))
    await db_session.execute(text("DELETE FROM community_pool WHERE name = 'r/testeval'"))

    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name,
                tier,
                categories,
                description_keywords,
                semantic_quality_score,
                is_active,
                is_blacklisted,
                created_at,
                updated_at
            )
            VALUES (
                'r/testeval',
                'candidate',
                '{}'::jsonb,
                '{}'::jsonb,
                0.5,
                true,
                false,
                :ts,
                :ts
            )
            """
        ),
        {"ts": now},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO discovered_communities (
                name,
                discovered_count,
                first_discovered_at,
                last_discovered_at,
                status,
                metrics,
                created_at,
                updated_at
            )
            VALUES (
                'r/testeval',
                1,
                :ts,
                :ts,
                'pending',
                CAST(:metrics AS jsonb),
                :ts,
                :ts
            )
            """
        ),
        {"ts": now, "metrics": '{"vetting":{"days":30,"status":"completed"}}'},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO posts_raw (
                source,
                source_post_id,
                version,
                created_at,
                fetched_at,
                valid_from,
                subreddit,
                title,
                body,
                is_current,
                score,
                num_comments
            )
            VALUES (
                'reddit',
                't3_eval',
                1,
                :ts,
                :ts,
                :ts,
                'r/testeval',
                'title',
                'body',
                true,
                10,
                2
            )
            """
        ),
        {"ts": now},
    )
    await db_session.commit()

    row = await db_session.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == "r/testeval")
    )
    community = row.scalar_one()

    class DummyRedditClient:
        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    evaluator = CommunityEvaluator(db_session, DummyRedditClient(), sample_size=10)
    posts = await evaluator._fetch_sample_posts_from_db(community)
    assert posts
    assert posts[0].id == "t3_eval"


@pytest.mark.asyncio
async def test_approve_community_inserts_pool_row(db_session) -> None:
    await db_session.execute(text("DELETE FROM discovered_communities WHERE name = 'r/testapprove'"))
    await db_session.execute(text("DELETE FROM community_pool WHERE name = 'r/testapprove'"))

    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name,
                tier,
                categories,
                description_keywords,
                semantic_quality_score,
                is_active,
                is_blacklisted,
                created_at,
                updated_at
            )
            VALUES (
                'r/testapprove',
                'candidate',
                '{}'::jsonb,
                '{}'::jsonb,
                0.5,
                false,
                false,
                :ts,
                :ts
            )
            """
        ),
        {"ts": now},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO discovered_communities (
                name,
                discovered_count,
                first_discovered_at,
                last_discovered_at,
                status,
                metrics,
                created_at,
                updated_at
            )
            VALUES (
                'r/testapprove',
                1,
                :ts,
                :ts,
                'pending',
                CAST(:metrics AS jsonb),
                :ts,
                :ts
            )
            """
        ),
        {"ts": now, "metrics": '{"vetting":{"days":30,"status":"completed"}}'},
    )
    await db_session.commit()

    row = await db_session.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == "r/testapprove")
    )
    community = row.scalar_one()

    class DummyRedditClient:
        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    evaluator = CommunityEvaluator(db_session, DummyRedditClient(), sample_size=10)
    result = await evaluator._approve_community(
        community,
        value_density=0.6,
        breakdown={"Growth": 1},
        sample_size=10,
        high_value_count=6,
    )
    assert result["status"] == "approved"

    pool_row = await db_session.execute(
        text(
            """
            SELECT description_keywords, is_active, tier
            FROM community_pool
            WHERE name = 'r/testapprove'
            """
        )
    )
    pool = pool_row.first()
    assert pool is not None
    assert pool[0] is not None


@pytest.mark.asyncio
async def test_approve_community_blocked_when_pool_blacklisted(db_session) -> None:
    await db_session.execute(
        text("DELETE FROM discovered_communities WHERE name = 'r/testblackapprove'")
    )
    await db_session.execute(
        text("DELETE FROM community_pool WHERE name = 'r/testblackapprove'")
    )

    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name,
                tier,
                categories,
                description_keywords,
                semantic_quality_score,
                is_active,
                is_blacklisted,
                created_at,
                updated_at
            )
            VALUES (
                'r/testblackapprove',
                'candidate',
                '{}'::jsonb,
                '{}'::jsonb,
                0.5,
                false,
                true,
                :ts,
                :ts
            )
            """
        ),
        {"ts": now},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO discovered_communities (
                name,
                discovered_count,
                first_discovered_at,
                last_discovered_at,
                status,
                metrics,
                created_at,
                updated_at
            )
            VALUES (
                'r/testblackapprove',
                1,
                :ts,
                :ts,
                'pending',
                CAST(:metrics AS jsonb),
                :ts,
                :ts
            )
            """
        ),
        {"ts": now, "metrics": '{"vetting":{"days":30,"status":"completed"}}'},
    )
    await db_session.commit()

    row = await db_session.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == "r/testblackapprove")
    )
    community = row.scalar_one()

    class DummyRedditClient:
        async def __aenter__(self) -> "DummyRedditClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    evaluator = CommunityEvaluator(db_session, DummyRedditClient(), sample_size=10)
    result = await evaluator._approve_community(
        community,
        value_density=0.9,
        breakdown={"Growth": 5},
        sample_size=10,
        high_value_count=9,
    )
    assert result["status"] == "blacklisted"

    pool_row = await db_session.execute(
        text(
            """
            SELECT is_active, is_blacklisted
            FROM community_pool
            WHERE name = 'r/testblackapprove'
            """
        )
    )
    pool = pool_row.first()
    assert pool is not None
    assert bool(pool[1]) is True
    assert bool(pool[0]) is False


@pytest.mark.asyncio
async def test_fetch_sample_posts_uses_clean_subreddit(db_session) -> None:
    class DummyRedditClient:
        def __init__(self) -> None:
            self.called: list[str] = []

        async def fetch_subreddit_posts(
            self, subreddit: str, *, sort: str, limit: int, time_filter: str = "week", after: str | None = None
        ):
            self.called.append(subreddit)
            return [], None

    dummy = DummyRedditClient()
    evaluator = CommunityEvaluator(db_session, dummy, sample_size=10)
    posts = await evaluator._fetch_sample_posts("r/reeftank")
    assert posts == []
    assert dummy.called == ["reeftank", "reeftank"]
