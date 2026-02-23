from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


async def _insert_community_pool(
    session, *, name: str, ts: datetime
) -> int:
    result = await session.execute(
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
                :name,
                'candidate',
                '{}'::jsonb,
                '{}'::jsonb,
                0.5,
                true,
                false,
                :ts,
                :ts
            )
            RETURNING id
            """
        ),
        {"name": name, "ts": ts},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_post_scores_latest_view_uses_is_latest() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text("TRUNCATE TABLE post_scores, posts_raw RESTART IDENTITY CASCADE")
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:pid, 'none', 'rulebook_v1', :ts, false, 2.0, 'lab')
                """
            ),
            {"pid": post_id, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:pid, 'llm-x', 'formal_v2', :ts, true, 8.0, 'core')
                """
            ),
            {"pid": post_id, "ts": now},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM post_scores_latest_v WHERE post_id = :pid"
                ),
                {"pid": post_id},
            )
        ).mappings().first()

    assert row is not None
    assert row["rule_version"] == "formal_v2"


@pytest.mark.asyncio
async def test_post_scores_latest_view_prefers_formal_rule_version() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text("TRUNCATE TABLE post_scores, posts_raw RESTART IDENTITY CASCADE")
        )

        now = datetime.now(timezone.utc)
        community_id_primary = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        community_id_formal = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_primary = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id_primary,
                },
            )
        ).scalar_one()
        post_formal = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id_formal,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:pid, 'none', 'rulebook_v1', :ts, true, 2.0, 'lab')
                """
            ),
            {"pid": post_primary, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:pid, 'llm-x', 'formal_v2', :ts, true, 8.0, 'core')
                """
            ),
            {"pid": post_formal, "ts": now},
        )
        await session.commit()

        formal_row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM post_scores_latest_v WHERE post_id = :pid"
                ),
                {"pid": post_formal},
            )
        ).mappings().first()
        bootstrap_row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM post_scores_latest_v WHERE post_id = :pid"
                ),
                {"pid": post_primary},
            )
        ).mappings().first()

        assert formal_row is not None
        assert formal_row["rule_version"] == "formal_v2"
        assert bootstrap_row is None


@pytest.mark.asyncio
async def test_comment_scores_latest_view_uses_is_latest() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE comment_scores, comments, posts_raw "
                "RESTART IDENTITY CASCADE"
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()
        comment_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO comments (
                        reddit_comment_id, source, source_post_id, post_id, subreddit,
                        depth, body, created_utc
                    )
                    VALUES (:cid, 'reddit', :pid, :post_id, 'r/test', 0, 'body', :ts)
                    RETURNING id
                    """
                ),
                {
                    "cid": f"t1_{uuid.uuid4().hex[:8]}",
                    "pid": "post_x",
                    "post_id": post_id,
                    "ts": now,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:cid, 'none', 'rulebook_v1', :ts, false, 1.0, 'lab')
                """
            ),
            {"cid": comment_id, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:cid, 'llm-x', 'formal_v2', :ts, true, 7.0, 'core')
                """
            ),
            {"cid": comment_id, "ts": now},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM comment_scores_latest_v WHERE comment_id = :cid"
                ),
                {"cid": comment_id},
            )
        ).mappings().first()

        assert row is not None
        assert row["rule_version"] == "formal_v2"


@pytest.mark.asyncio
async def test_comment_scores_latest_view_prefers_formal_rule_version() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE comment_scores, comments, posts_raw "
                "RESTART IDENTITY CASCADE"
            )
        )

        now = datetime.now(timezone.utc)
        community_primary = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        community_formal = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_primary = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_primary,
                },
            )
        ).scalar_one()
        post_formal = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_formal,
                },
            )
        ).scalar_one()
        comment_primary = (
            await session.execute(
                text(
                    """
                    INSERT INTO comments (
                        reddit_comment_id, source, source_post_id, post_id, subreddit,
                        depth, body, created_utc
                    )
                    VALUES (:cid, 'reddit', :pid, :post_id, 'r/test', 0, 'body', :ts)
                    RETURNING id
                    """
                ),
                {
                    "cid": f"t1_{uuid.uuid4().hex[:8]}",
                    "pid": "post_a",
                    "post_id": post_primary,
                    "ts": now,
                },
            )
        ).scalar_one()
        comment_formal = (
            await session.execute(
                text(
                    """
                    INSERT INTO comments (
                        reddit_comment_id, source, source_post_id, post_id, subreddit,
                        depth, body, created_utc
                    )
                    VALUES (:cid, 'reddit', :pid, :post_id, 'r/test', 0, 'body', :ts)
                    RETURNING id
                    """
                ),
                {
                    "cid": f"t1_{uuid.uuid4().hex[:8]}",
                    "pid": "post_b",
                    "post_id": post_formal,
                    "ts": now,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:cid, 'none', 'rulebook_v1', :ts, true, 1.0, 'lab')
                """
            ),
            {"cid": comment_primary, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:cid, 'llm-x', 'formal_v2', :ts, true, 7.0, 'core')
                """
            ),
            {"cid": comment_formal, "ts": now},
        )
        await session.commit()

        formal_row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM comment_scores_latest_v WHERE comment_id = :cid"
                ),
                {"cid": comment_formal},
            )
        ).mappings().first()
        bootstrap_row = (
            await session.execute(
                text(
                    "SELECT rule_version FROM comment_scores_latest_v WHERE comment_id = :cid"
                ),
                {"cid": comment_primary},
            )
        ).mappings().first()

        assert formal_row is not None
        assert formal_row["rule_version"] == "formal_v2"
        assert bootstrap_row is None


@pytest.mark.asyncio
async def test_post_scores_latest_view_overrides_noise_labels() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE noise_labels, post_scores, posts_raw "
                "RESTART IDENTITY CASCADE"
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:pid, 'llm-x', 'formal_v2', :ts, true, 9.0, 'core')
                """
            ),
            {"pid": post_id, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO noise_labels (content_type, content_id, noise_type, reason)
                VALUES ('post', :pid, 'spam_manual', 'test')
                """
            ),
            {"pid": post_id},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    """
                    SELECT business_pool, value_score
                    FROM post_scores_latest_v
                    WHERE post_id = :pid
                    """
                ),
                {"pid": post_id},
            )
        ).mappings().first()

    assert row is not None
    assert row["business_pool"] == "noise"
    assert float(row["value_score"]) == 0.0


@pytest.mark.asyncio
async def test_comment_scores_latest_view_overrides_noise_labels() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE noise_labels, comment_scores, comments, posts_raw "
                "RESTART IDENTITY CASCADE"
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES ('reddit', :pid, 1, :ts, :ts, :ts, 'r/test', 'title', 'body', true, :community_id)
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()
        comment_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO comments (
                        reddit_comment_id, source, source_post_id, post_id, subreddit,
                        depth, body, created_utc
                    )
                    VALUES (:cid, 'reddit', :pid, :post_id, 'r/test', 0, 'body', :ts)
                    RETURNING id
                    """
                ),
                {
                    "cid": f"t1_{uuid.uuid4().hex[:8]}",
                    "pid": "post_x",
                    "post_id": post_id,
                    "ts": now,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool
                )
                VALUES (:cid, 'llm-x', 'formal_v2', :ts, true, 6.0, 'core')
                """
            ),
            {"cid": comment_id, "ts": now},
        )
        await session.execute(
            text(
                """
                INSERT INTO noise_labels (content_type, content_id, noise_type, reason)
                VALUES ('comment', :cid, 'spam_manual', 'test')
                """
            ),
            {"cid": comment_id},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    """
                    SELECT business_pool, value_score
                    FROM comment_scores_latest_v
                    WHERE comment_id = :cid
                    """
                ),
                {"cid": comment_id},
            )
        ).mappings().first()

    assert row is not None
    assert row["business_pool"] == "noise"
    assert float(row["value_score"]) == 0.0
