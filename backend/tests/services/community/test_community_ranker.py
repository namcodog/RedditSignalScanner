from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from app.services.analysis.community_ranker import compute_ranking_scores


@pytest.mark.asyncio
async def test_compute_ranking_scores_prefers_higher_pain_brand_and_growth(db_session):
    now = datetime.now(timezone.utc)

    # ensure clean slate for id/unique constraints
    for tbl in ("content_entities", "content_labels", "comments", "posts_hot", "subreddit_snapshots"):
        await db_session.execute(text(f"DELETE FROM {tbl}"))

    # Community A: more pain comments, brand mentions, better growth
    try:
        await db_session.execute(
            text(
                """
                INSERT INTO comments (id, reddit_comment_id, source, source_post_id, subreddit, body, created_utc, score, permalink)
                VALUES
                  (3301, 't1_A1', 'reddit', 'p_A1', 'r/A', 'Hate the subscription fee, really bad', :t7, 20, '/r/A/comments/p_A1/c1'),
                  (3302, 't1_A2', 'reddit', 'p_A2', 'r/A', 'BrandX is too expensive', :t7, 10, '/r/A/comments/p_A2/c2')
                """
            ),
            {"t7": now - timedelta(days=3)},
        )
    except Exception as e:  # pragma: no cover - debug aid
        assert False, f"failed to insert comments: {e}"
    await db_session.execute(
        text(
            """
            INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
            VALUES
              ('comment', 3301, 'pain', 'subscription', 90),
              ('comment', 3302, 'pain', 'price', 90)
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
            VALUES ('comment', 3302, 'BrandX', 'brand', 1)
            """
        )
    )
    # posts_hot for growth 7/30
    for i in range(3):
        await db_session.execute(
            text(
                """
                INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
                VALUES (:id, 'reddit', :pid, :t7p, :exp, 't', 'b', 'r/A', 1, 0, '{}'::jsonb)
                """
            ),
            {
                "id": 3100 + i,
                "pid": f"pA{i}",
                "t7p": now - timedelta(days=2),
                "exp": now + timedelta(days=5),
            },
        )
    for i in range(4):
        await db_session.execute(
            text(
                """
                INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
                VALUES (:id, 'reddit', :pid, :t30p, :exp, 't', 'b', 'r/A', 1, 0, '{}'::jsonb)
                """
            ),
            {
                "id": 3200 + i,
                "pid": f"pA30_{i}",
                "t30p": now - timedelta(days=20),
                "exp": now + timedelta(days=10),
            },
        )

    # Community B: fewer pain and no brand
    await db_session.execute(
        text(
            """
            INSERT INTO comments (id, reddit_comment_id, source, source_post_id, subreddit, body, created_utc, score, permalink)
            VALUES (4301, 't1_B1', 'reddit', 'p_B1', 'r/B', 'Nice workaround, recommend trying', :t7, 5, '/r/B/comments/p_B1/c1')
            """
        ),
        {"t7": now - timedelta(days=5)},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
            VALUES ('comment', 4001, 'solution', 'other', 80)
            """
        )
    )

    await db_session.commit()

    scores = await compute_ranking_scores(db_session, ["r/A", "r/B"], since_days_7=7, since_days_30=30)
    print("RANKING SCORES:", scores)
    assert set(scores.keys()) == {"r/A", "r/B"}
    assert scores["r/A"] > scores["r/B"]
