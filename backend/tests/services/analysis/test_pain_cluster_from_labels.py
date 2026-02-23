from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from app.services.analysis.pain_cluster import cluster_pain_points_from_labels


@pytest.mark.asyncio
async def test_cluster_pain_points_from_labels_minimal(db_session):
    """DB-backed clustering returns non-empty clusters with required fields.

    We insert a few comments and posts with pain labels, then expect at least
    one cluster with topic/samples present. Comments should be preferred in
    samples selection.
    """
    now = datetime.now(timezone.utc)

    # Insert two comments under different subreddits
    await db_session.execute(
        text(
            """
            INSERT INTO comments (reddit_comment_id, source, source_post_id, subreddit, body, created_utc, score, permalink)
            VALUES
              ('t1_a', 'reddit', 'p_a', 'r/testA', 'I hate the pricing changes, too expensive.', :now, 15, '/r/testA/comments/p_a/c_a'),
              ('t1_b', 'reddit', 'p_b', 'r/testB', 'Subscription fee is annoying and a problem.', :now, 5, '/r/testB/comments/p_b/c_b')
            """
        ),
        {"now": now - timedelta(days=1)},
    )

    # Add labels for the comments (pain)
    await db_session.execute(
        text(
            """
            INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
            VALUES
              ('comment', 1001, 'pain', 'price', 90),
              ('comment', 1002, 'pain', 'subscription', 80)
            """
        )
    )

    # Insert a recent post in hot cache and label it as pain (as fallback)
    await db_session.execute(
        text(
            """
            INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
            VALUES (2001, 'reddit', 'p_c', :now, :exp, 'Install is too hard', 'Wall mount is painful', 'r/testA', 12, 3, '{}'::jsonb)
            """
        ),
        {"now": now - timedelta(days=2), "exp": now + timedelta(days=1)},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
            VALUES ('post', 2001, 'pain', 'install', 85)
            """
        )
    )

    await db_session.commit()

    clusters = await cluster_pain_points_from_labels(db_session, since_days=30)
    assert isinstance(clusters, list)
    assert len(clusters) >= 1
    first = clusters[0]
    # required fields
    for key in ("topic", "negative_mean", "communities_count", "top_communities", "samples"):
        assert key in first
    # samples should be non-empty and strings
    assert isinstance(first["samples"], list)
    assert all(isinstance(s, str) and len(s) > 0 for s in first["samples"])
