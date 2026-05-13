from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.services.labeling.labeling_posts import label_posts_recent


@pytest.mark.asyncio
async def test_label_posts_recent_refreshes_semantic_observation(
    db_session,
    async_truncate_test_tables,
) -> None:
    await async_truncate_test_tables(
        "semantic_observation",
        "content_entities",
        "content_labels",
        "posts_hot",
    )
    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            """
            INSERT INTO posts_hot (
                id, source, source_post_id, created_at, expires_at,
                title, body, subreddit, score, num_comments, metadata
            ) VALUES (
                91001, 'reddit', 't3_semantic_post', :created_at, :expires_at,
                'Tonal subscription pain',
                'Tonal subscription is too expensive for family users.',
                'r/homegym', 12, 5, '{}'::jsonb
            )
            """
        ),
        {"created_at": now, "expires_at": now + timedelta(days=7)},
    )
    await db_session.commit()

    result = await label_posts_recent(db_session, since_days=7, limit=20)

    assert result["labeled"] == 1

    row = (
        await db_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM semantic_observation
                WHERE content_type = 'post' AND content_id = 91001
                """
            )
        )
    ).scalar_one()
    assert int(row) >= 1
