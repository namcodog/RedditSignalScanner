from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.crawl import comments_ingest


@pytest.mark.asyncio
async def test_persist_comments_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE comments, authors, posts_quarantine, posts_raw, community_pool RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        now = datetime.now(timezone.utc)
        subreddit = f"r/test_{uuid.uuid4().hex[:8]}"
        session.add(
            CommunityPool(
                name=subreddit,
                tier="silver",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                priority="medium",
                is_active=True,
                is_blacklisted=False,
            )
        )
        await session.flush()

        source_post_id = f"t3_comments_{uuid.uuid4().hex[:8]}"
        await session.execute(
            text(
                """
                INSERT INTO posts_raw (
                    source, source_post_id, version, created_at, fetched_at, valid_from,
                    subreddit, title, body, is_current
                )
                VALUES ('reddit', :pid, 1, :ts, :ts, :ts, :subreddit, 'title', 'body', true)
                """
            ),
            {"pid": source_post_id, "ts": now, "subreddit": subreddit},
        )
        await session.commit()

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

        n1 = await comments_ingest.persist_comments(
            session,
            source_post_id=source_post_id,
            subreddit=subreddit,
            comments=items,
        )
        n2 = await comments_ingest.persist_comments(
            session,
            source_post_id=source_post_id,
            subreddit=subreddit,
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
        await session.execute(
            text(
                "TRUNCATE TABLE comments, authors, posts_quarantine, posts_raw, community_pool RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        run_id = str(uuid.uuid4())
        community_run_id = str(uuid.uuid4())
        source_post_id = f"t3_runid_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        subreddit = "r/test"

        session.add(
            CommunityPool(
                name=subreddit,
                tier="silver",
                categories={"topic": ["ops"]},
                description_keywords={"keywords": ["ops"]},
                priority="medium",
                is_active=True,
                is_blacklisted=False,
            )
        )
        await session.flush()

        # Ensure a matching posts_raw row exists (persist_comments resolves post_id).
        await session.execute(
            text(
                """
                INSERT INTO posts_raw (source, source_post_id, version, created_at, fetched_at, valid_from, subreddit, title, body, is_current)
                VALUES ('reddit', :pid, 1, :ts, :ts, :ts, :subreddit, 'title', 'body', true)
                """
            ),
            {"pid": source_post_id, "ts": now, "subreddit": subreddit},
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

        n = await comments_ingest.persist_comments(
            session,
            source_post_id=source_post_id,
            subreddit=subreddit,
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


def test_build_comment_upsert_sql_is_cached_and_flag_driven() -> None:
    with_expires = comments_ingest._build_comment_upsert_sql(
        has_expires=True,
        has_post_id=True,
        has_crawl_run_id=True,
        has_community_run_id=True,
    )
    same_again = comments_ingest._build_comment_upsert_sql(
        has_expires=True,
        has_post_id=True,
        has_crawl_run_id=True,
        has_community_run_id=True,
    )
    legacy = comments_ingest._build_comment_upsert_sql(
        has_expires=False,
        has_post_id=False,
        has_crawl_run_id=False,
        has_community_run_id=False,
    )

    assert with_expires is same_again
    assert "expires_at" in str(with_expires)
    assert "community_run_id" in str(with_expires)
    assert "post_id = COALESCE" in str(with_expires)
    assert "expires_at" not in str(legacy)
    assert "community_run_id" not in str(legacy)
    assert "post_id = COALESCE" not in str(legacy)


@pytest.mark.asyncio
async def test_persist_comments_logs_when_post_fk_cannot_be_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.crawl.comments_ingest as comments_ingest_module

    monkeypatch.setattr(comments_ingest_module, "_COMMENTS_HAS_POST_ID", True)
    monkeypatch.setattr(comments_ingest_module, "_COMMENTS_HAS_EXPIRES", False)
    monkeypatch.setattr(comments_ingest_module, "_COMMENTS_HAS_CRAWL_RUN_ID", False)
    monkeypatch.setattr(comments_ingest_module, "_COMMENTS_HAS_COMMUNITY_RUN_ID", False)
    warning_messages: list[str] = []

    def capture_warning(message: str, *args: object, **_: object) -> None:
        warning_messages.append(message % args if args else message)

    monkeypatch.setattr(comments_ingest_module.logger, "warning", capture_warning)

    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        items = [
            {
                "id": "t1_missing_post_fk",
                "body": "missing post link should be visible",
                "created_utc": int(now.timestamp()),
                "depth": 0,
                "score": 2,
                "author": "u_fk",
            }
        ]

        processed = await comments_ingest.persist_comments(
            session,
            source_post_id="t3_missing_fk_target",
            subreddit="r/homegym",
            comments=items,
        )

    assert processed == 0
    assert any("post_id resolution failed" in message for message in warning_messages)
