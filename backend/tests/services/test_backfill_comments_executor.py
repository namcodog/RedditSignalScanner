from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_fetches_and_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    captured: dict[str, Any] = {}

    async def fake_persist_comments(
        session: Any,
        *,
        source_post_id: str,
        subreddit: str,
        comments: list[dict[str, Any]],
        crawl_run_id: str,
        community_run_id: str,
        source_track: str | None = None,
        default_business_pool: str | None = None,
        **__: Any,
    ) -> int:
        captured["source_post_id"] = source_post_id
        captured["subreddit"] = subreddit
        captured["count"] = len(comments)
        captured["crawl_run_id"] = crawl_run_id
        captured["community_run_id"] = community_run_id
        captured["source_track"] = source_track
        captured["default_business_pool"] = default_business_pool
        return len(comments)

    class DummyReddit:
        async def fetch_post_comments(
            self,
            post_id: str,
            *,
            sort: str,
            depth: int,
            limit: int,
            mode: str,
            smart_config: dict[str, Any] | None = None,
        ) -> list[dict[str, Any]]:
            return [
                {"id": "c1", "body": "hello"},
                {"id": "c2", "body": "world"},
            ][: int(limit)]

    monkeypatch.setattr(execute_plan_module, "persist_comments", fake_persist_comments)

    plan = CrawlPlanContract(
        plan_kind="backfill_comments",
        target_type="post_ids",
        target_value="post_123",
        reason="candidate_vetting_comments",
        limits=CrawlPlanLimits(comments_limit=50),
        meta={
            "subreddit": "r/testsub",
            "mode": "full",
            "depth": 2,
            "sort": "confidence",
            "label_after_ingest": False,
        },
    )

    async with SessionFactory() as session:
        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert captured["source_post_id"] == "post_123"
    assert captured["subreddit"] == "r/testsub"
    assert captured["count"] == 2
    assert captured["crawl_run_id"] == "run"
    assert captured["community_run_id"] == "community"
    assert captured["source_track"] == "backfill_comments"
    assert out["status"] in {"completed", "partial"}


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_maps_internal_post_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    captured: dict[str, Any] = {}
    source_post_id = f"t3_internal_{uuid.uuid4().hex}"

    async def fake_persist_comments(
        session: Any,
        *,
        source_post_id: str,
        subreddit: str,
        comments: list[dict[str, Any]],
        crawl_run_id: str,
        community_run_id: str,
        **__: Any,
    ) -> int:
        captured["source_post_id"] = source_post_id
        captured["subreddit"] = subreddit
        return len(comments)

    class DummyReddit:
        async def fetch_post_comments(
            self,
            post_id: str,
            *,
            sort: str,
            depth: int,
            limit: int,
            mode: str,
            smart_config: dict[str, Any] | None = None,
        ) -> list[dict[str, Any]]:
            captured["fetched_post_id"] = post_id
            return [{"id": "c1", "body": "hello"}]

    monkeypatch.setattr(execute_plan_module, "persist_comments", fake_persist_comments)

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        row = await session.execute(
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
                    :pid,
                    1,
                    :ts,
                    :ts,
                    :ts,
                    'r/testsub',
                    'title',
                    'body',
                    true,
                    10,
                    2
                )
                RETURNING id
                """
            ),
            {"pid": source_post_id, "ts": now},
        )
        internal_id = row.scalar_one()
        await session.commit()

        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=str(internal_id),
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={
                "subreddit": "r/testsub",
                "mode": "full",
                "depth": 2,
                "sort": "confidence",
                "label_after_ingest": False,
            },
        )

        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert captured["fetched_post_id"] == source_post_id
    assert captured["source_post_id"] == source_post_id
    assert captured["subreddit"] == "r/testsub"
    assert out["status"] in {"completed", "partial"}


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_smart_shallow_does_not_boost_for_blast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    captured: dict[str, Any] = {}

    async def fake_persist_comments(
        session: Any,
        *,
        source_post_id: str,
        subreddit: str,
        comments: list[dict[str, Any]],
        crawl_run_id: str,
        community_run_id: str,
        **__: Any,
    ) -> int:
        captured["source_post_id"] = source_post_id
        captured["subreddit"] = subreddit
        return len(comments)

    class DummyReddit:
        async def fetch_post_comments(
            self,
            post_id: str,
            *,
            sort: str,
            depth: int,
            limit: int,
            mode: str,
            smart_config: dict[str, Any] | None = None,
        ) -> list[dict[str, Any]]:
            captured["mode"] = mode
            captured["depth"] = depth
            captured["limit"] = limit
            captured["smart_config"] = smart_config
            return [{"id": "c1", "body": "hello"}]

    monkeypatch.setattr(execute_plan_module, "persist_comments", fake_persist_comments)

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        blast_post_id = f"post_blast_{uuid.uuid4().hex}"
        await session.execute(
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
                    :pid,
                    1,
                    :ts,
                    :ts,
                    :ts,
                    'r/testsub',
                    'title',
                    'body',
                    true,
                    600,
                    400
                )
                """
            ),
            {"ts": now, "pid": blast_post_id},
        )
        await session.commit()

        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=blast_post_id,
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={
                "subreddit": "r/testsub",
            },
        )

        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert out["status"] in {"completed", "partial"}
    assert captured["mode"] == "smart_shallow"
    assert captured["depth"] == 2
    assert captured["limit"] == 50
    assert captured["smart_config"]["smart_total_limit"] == 50
    assert captured["smart_config"]["smart_top_limit"] == 30
    assert captured["smart_config"]["smart_new_limit"] == 20
    assert captured["smart_config"]["smart_reply_top_limit"] == 15


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_smart_shallow_old_post_uses_top_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    captured: dict[str, Any] = {}

    async def fake_persist_comments(
        session: Any,
        *,
        source_post_id: str,
        subreddit: str,
        comments: list[dict[str, Any]],
        crawl_run_id: str,
        community_run_id: str,
        **__: Any,
    ) -> int:
        captured["source_post_id"] = source_post_id
        captured["subreddit"] = subreddit
        return len(comments)

    class DummyReddit:
        async def fetch_post_comments(
            self,
            post_id: str,
            *,
            sort: str,
            depth: int,
            limit: int,
            mode: str,
            smart_config: dict[str, Any] | None = None,
        ) -> list[dict[str, Any]]:
            captured["mode"] = mode
            captured["depth"] = depth
            captured["limit"] = limit
            captured["smart_config"] = smart_config
            return [{"id": "c1", "body": "hello"}]

    monkeypatch.setattr(execute_plan_module, "persist_comments", fake_persist_comments)

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        old_post_id = f"post_old_{uuid.uuid4().hex}"
        await session.execute(
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
                    :pid,
                    1,
                    :ts,
                    :ts,
                    :ts,
                    'r/testsub',
                    'title',
                    'body',
                    true,
                    10,
                    80
                )
                """
            ),
            {"ts": now - timedelta(days=10), "pid": old_post_id},
        )
        await session.commit()

        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=old_post_id,
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={
                "subreddit": "r/testsub",
            },
        )

        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert out["status"] in {"completed", "partial"}
    assert captured["mode"] == "smart_shallow"
    assert captured["depth"] == 2
    assert captured["limit"] == 50
    assert captured["smart_config"]["smart_total_limit"] == 50
    assert captured["smart_config"]["smart_new_limit"] == 0
    assert captured["smart_config"]["smart_top_limit"] == 40


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_skips_when_no_comments() -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    class DummyReddit:
        async def fetch_post_comments(self, *_: Any, **__: Any) -> list[dict[str, Any]]:
            raise AssertionError("should not fetch when num_comments=0")

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        empty_post_id = f"post_empty_{uuid.uuid4().hex}"
        await session.execute(
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
                    :pid,
                    1,
                    :ts,
                    :ts,
                    :ts,
                    'r/testsub',
                    'title',
                    'body',
                    true,
                    0,
                    0
                )
                """
            ),
            {"ts": now, "pid": empty_post_id},
        )
        await session.commit()

        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=empty_post_id,
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={
                "subreddit": "r/testsub",
            },
        )

        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert out["status"] == "completed"
    assert out["processed"] == 0
    assert out["reason"] == "no_comments"


@pytest.mark.asyncio
async def test_execute_crawl_plan_backfill_comments_skips_when_up_to_date() -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    class DummyReddit:
        async def fetch_post_comments(self, *_: Any, **__: Any) -> list[dict[str, Any]]:
            raise AssertionError("should not fetch when comments already ingested")

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        post_id = f"post_uptodate_{uuid.uuid4().hex}"
        await session.execute(
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
                    :pid,
                    1,
                    :ts,
                    :ts,
                    :ts,
                    'r/testsub',
                    'title',
                    'body',
                    true,
                    10,
                    2
                )
                """
            ),
            {"ts": now, "pid": post_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id,
                    source,
                    source_post_id,
                    subreddit,
                    body,
                    created_utc
                )
                VALUES
                    (:cid1, 'reddit', :pid, 'r/testsub', 'a', :ts),
                    (:cid2, 'reddit', :pid, 'r/testsub', 'b', :ts)
                """
            ),
            {
                "ts": now,
                "pid": post_id,
                "cid1": uuid.uuid4().hex[:32],
                "cid2": uuid.uuid4().hex[:32],
            },
        )
        await session.commit()

        plan = CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value=post_id,
            reason="manual_backfill_comments",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={
                "subreddit": "r/testsub",
            },
        )

        out = await execute_plan_module.execute_crawl_plan(
            plan=plan,
            session=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="community",
        )

    assert out["status"] == "completed"
    assert out["processed"] == 0
    assert out["reason"] == "already_up_to_date"
