from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.crawl import backfill_posts_workflow
from app.services.infrastructure.reddit_client import RedditPost


async def _seed_cache_community(
    session: Any, *, community_name: str, now: datetime
) -> None:
    session.add(
        CommunityPool(
            name=community_name,
            tier="medium",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=10,
            priority="medium",
        )
    )
    await session.flush()
    session.add(
        CommunityCache(
            community_name=community_name,
            last_crawled_at=now,
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.50"),
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_backfill_posts_workflow_returns_partial_when_budget_hit_without_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    community_name = f"r/test_backfill_workflow_empty_budget_{uuid.uuid4().hex[:8]}"

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            created = (until + timedelta(hours=1)).timestamp()
            post = RedditPost(
                id="p_future",
                title="future",
                selftext="",
                score=1,
                num_comments=0,
                created_utc=float(created),
                subreddit="test",
                author="a",
                url="",
                permalink="",
            )
            return [post], "t3_next"

    monkeypatch.setenv("BACKFILL_MAX_PAGES_PER_RUN", "1")

    async with SessionFactory() as session:
        await _seed_cache_community(session, community_name=community_name, now=now)

        result = await backfill_posts_workflow.execute_backfill_posts_workflow(
            workflow_input=backfill_posts_workflow.BackfillPostsWorkflowInput(
                community_name=community_name,
                since=since,
                until=until,
                max_posts=10,
                sort="new",
                after=None,
                session=session,
                reddit_client=DummyReddit(),
            ),
            deps=backfill_posts_workflow.BackfillPostsWorkflowDeps(
                dual_write=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "dual_write should not run when no posts survive window"
                    )
                ),
            ),
        )

    assert result.payload["status"] == "partial"
    assert result.payload["reason"] == "budget_remaining"
    assert result.payload["total_fetched"] == 0
    assert result.payload["api_calls_total"] == 1


@pytest.mark.asyncio
async def test_backfill_posts_workflow_updates_waterlines_after_success() -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    newer = (since + timedelta(hours=5)).timestamp()
    older = (since + timedelta(hours=1)).timestamp()
    captured: dict[str, Any] = {}
    community_name = f"r/test_backfill_workflow_success_{uuid.uuid4().hex[:8]}"

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            return (
                [
                    RedditPost(
                        id="p_new",
                        title="new",
                        selftext="",
                        score=1,
                        num_comments=0,
                        created_utc=float(newer),
                        subreddit="test",
                        author="a",
                        url="",
                        permalink="",
                    ),
                    RedditPost(
                        id="p_old",
                        title="old",
                        selftext="",
                        score=1,
                        num_comments=0,
                        created_utc=float(older),
                        subreddit="test",
                        author="a",
                        url="",
                        permalink="",
                    ),
                ],
                None,
            )

    async def _fake_dual_write(
        community_name: str,
        posts: list[RedditPost],
        *,
        trigger_comments_fetch: bool,
    ) -> tuple[int, int, int]:
        captured["community_name"] = community_name
        captured["posts"] = [post.id for post in posts]
        captured["trigger_comments_fetch"] = trigger_comments_fetch
        return 2, 1, 0

    async def _fake_update_floor(
        name: str, *, backfill_floor: datetime, session: Any
    ) -> None:
        captured["floor_name"] = name
        captured["backfill_floor"] = backfill_floor

    async def _fake_update_waterline(
        name: str,
        *,
        last_seen_post_id: str,
        last_seen_created_at: datetime,
        session: Any,
    ) -> None:
        captured["waterline_name"] = name
        captured["last_seen_post_id"] = last_seen_post_id
        captured["last_seen_created_at"] = last_seen_created_at

    async with SessionFactory() as session:
        await _seed_cache_community(session, community_name=community_name, now=now)

        result = await backfill_posts_workflow.execute_backfill_posts_workflow(
            workflow_input=backfill_posts_workflow.BackfillPostsWorkflowInput(
                community_name=community_name,
                since=since,
                until=until,
                max_posts=10,
                sort="new",
                after=None,
                session=session,
                reddit_client=DummyReddit(),
            ),
            deps=backfill_posts_workflow.BackfillPostsWorkflowDeps(
                dual_write=_fake_dual_write,
                update_backfill_floor=_fake_update_floor,
                update_incremental_waterline=_fake_update_waterline,
            ),
        )

    assert captured["community_name"] == community_name
    assert captured["posts"] == ["p_new", "p_old"]
    assert captured["trigger_comments_fetch"] is False
    assert captured["floor_name"] == community_name
    assert captured["waterline_name"] == community_name
    assert captured["last_seen_post_id"] == "p_new"
    assert result.payload["status"] == "completed"
    assert result.payload["new_posts"] == 2
    assert result.payload["updated_posts"] == 1
    assert result.payload["duplicates"] == 0
