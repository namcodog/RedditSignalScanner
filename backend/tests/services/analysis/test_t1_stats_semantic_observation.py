from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import text

from app.models.community_pool import CommunityPool
from app.models.semantic_observation import SemanticObservation
from app.services.analysis import t1_stats
from app.services.crawl.comments_ingest import persist_comments


@pytest.mark.asyncio
async def test_t1_stats_reads_semantic_observation_for_core_aggregates(db_session) -> None:
    now = datetime.now(timezone.utc)
    subreddit = f"r/t1_sem_{uuid.uuid4().hex[:8]}"
    source_post_a = f"p_a_{uuid.uuid4().hex[:8]}"
    source_post_b = f"p_b_{uuid.uuid4().hex[:8]}"
    comment_a = f"t1_sem_a_{uuid.uuid4().hex[:8]}"
    comment_b = f"t1_sem_b_{uuid.uuid4().hex[:8]}"
    db_session.add(
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
    await db_session.flush()
    await db_session.execute(
        text(
            """
            INSERT INTO posts_raw (
              source, source_post_id, version, created_at, fetched_at, valid_from,
              subreddit, title, body, is_current
            )
            VALUES
              ('reddit', :post_a, 1, :created_at, :created_at, :created_at, :subreddit, 'title a', 'body a', true),
              ('reddit', :post_b, 1, :created_at, :created_at, :created_at, :subreddit, 'title b', 'body b', true)
            """
        ),
        {
            "post_a": source_post_a,
            "post_b": source_post_b,
            "subreddit": subreddit,
            "created_at": now - timedelta(days=1),
        },
    )
    await db_session.commit()
    await persist_comments(
        db_session,
        source_post_id=source_post_a,
        subreddit=subreddit,
        comments=[
            {
                "id": comment_a,
                "body": "price pain",
                "created_utc": int((now - timedelta(days=1)).timestamp()),
                "score": 12,
                "author": "alice",
            }
        ],
    )
    await persist_comments(
        db_session,
        source_post_id=source_post_b,
        subreddit=subreddit,
        comments=[
            {
                "id": comment_b,
                "body": "solution comment",
                "created_utc": int((now - timedelta(days=1)).timestamp()),
                "score": 6,
                "author": "bob",
            }
        ],
    )
    comment_rows = await db_session.execute(
        text(
            """
            SELECT id, reddit_comment_id
            FROM comments
            WHERE reddit_comment_id IN (:comment_a, :comment_b)
            """
        ),
        {"comment_a": comment_a, "comment_b": comment_b},
    )
    comment_ids = {str(row.reddit_comment_id): int(row.id) for row in comment_rows.fetchall()}

    db_session.add_all(
        [
            SemanticObservation(
                content_type="comment",
                content_id=comment_ids[comment_a],
                observation_type="content_label",
                label_key="pain",
                label_value="price",
                confidence=0.9,
                provenance="reconciled",
                run_key=f"comment:{comment_ids[comment_a]}:pain",
                source_model="content_labels",
                evidence={"source": "content_labels"},
                observed_at=now,
            ),
            SemanticObservation(
                content_type="comment",
                content_id=comment_ids[comment_a],
                observation_type="content_entity",
                label_key="brand",
                label_value="BrandX",
                confidence=1.0,
                provenance="reconciled",
                run_key=f"comment:{comment_ids[comment_a]}:brand",
                source_model="content_entities",
                evidence={"source": "content_entities"},
                observed_at=now,
            ),
            SemanticObservation(
                content_type="comment",
                content_id=comment_ids[comment_b],
                observation_type="content_label",
                label_key="solution",
                label_value="other",
                confidence=0.8,
                provenance="reconciled",
                run_key=f"comment:{comment_ids[comment_b]}:solution",
                source_model="content_labels",
                evidence={"source": "content_labels"},
                observed_at=now,
            ),
        ]
    )
    await db_session.commit()

    since_dt = now - timedelta(days=30)
    ratios = await t1_stats._fetch_ps_ratio_by_sub(
        db_session,
        subs=[subreddit.lower()],
        since_dt=since_dt,
    )
    aspects = await t1_stats._fetch_aspect_breakdown(
        db_session,
        subs=[subreddit.lower()],
        since_dt=since_dt,
    )
    brand_pain = await t1_stats._fetch_brand_pain_cooccurrence(
        db_session,
        subs=[subreddit.lower()],
        since_dt=since_dt,
        limit=5,
    )

    assert ratios[subreddit.lower()] == (1, 1)
    assert aspects[0].aspect == "price"
    assert aspects[0].pain == 1
    assert aspects[0].total == 1
    assert len(brand_pain) == 1
    assert brand_pain[0].brand == "BrandX"
    assert brand_pain[0].mentions == 1
    assert brand_pain[0].aspects == ["price"]
