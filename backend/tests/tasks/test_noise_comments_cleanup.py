from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.tasks.maintenance_task import cleanup_noise_comments_impl


@pytest.mark.asyncio
async def test_cleanup_noise_comments_only_deletes_noise_pool() -> None:
    now = datetime.now(timezone.utc)
    expired_at = now - timedelta(days=1)
    captured_at = now - timedelta(days=365)

    async with SessionFactory() as session:
        source_post_id = f"t3_noise_cleanup_{uuid.uuid4().hex[:8]}"

        noise_cid = f"t1_noise_{uuid.uuid4().hex[:8]}"
        lab_cid = f"t1_lab_{uuid.uuid4().hex[:8]}"

        await session.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id, source, source_post_id, subreddit,
                    depth, body, created_utc, score, captured_at, expires_at, business_pool
                ) VALUES
                    (:noise_cid, 'reddit', :pid, 'r/test', 0, 'noise', :ts, 0, :captured, :expired, 'noise'),
                    (:lab_cid,   'reddit', :pid, 'r/test', 0, 'lab',   :ts, 0, :captured, :expired, 'lab')
                """
            ),
            {
                "noise_cid": noise_cid,
                "lab_cid": lab_cid,
                "pid": source_post_id,
                "ts": now,
                "captured": captured_at,
                "expired": expired_at,
            },
        )
        rows = await session.execute(
            text(
                """
                SELECT id, reddit_comment_id
                FROM comments
                WHERE reddit_comment_id IN (:c1, :c2)
                """
            ),
            {"c1": noise_cid, "c2": lab_cid},
        )
        ids = {str(r[1]): int(r[0]) for r in rows.fetchall()}
        noise_id = ids[noise_cid]
        lab_id = ids[lab_cid]

        # Attach labels/entities to both; only noise-linked rows should be removed.
        await session.execute(
            text(
                "INSERT INTO content_labels (content_type, content_id, category, aspect, confidence) "
                "VALUES ('comment', :cid, 'pain', 'other', 80)"
            ),
            {"cid": noise_id},
        )
        await session.execute(
            text(
                "INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) "
                "VALUES ('comment', :cid, 'x', 'brand', 1)"
            ),
            {"cid": noise_id},
        )
        await session.execute(
            text(
                "INSERT INTO content_labels (content_type, content_id, category, aspect, confidence) "
                "VALUES ('comment', :cid, 'pain', 'other', 80)"
            ),
            {"cid": lab_id},
        )
        await session.execute(
            text(
                "INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) "
                "VALUES ('comment', :cid, 'y', 'brand', 1)"
            ),
            {"cid": lab_id},
        )
        await session.commit()

    result = await cleanup_noise_comments_impl(
        skip_guard=True, batch_size=100, max_batches=10, expired_only=True
    )
    assert result["deleted_comments"] == 1

    async with SessionFactory() as session:
        noise_exists = await session.execute(
            text("SELECT COUNT(*) FROM comments WHERE id=:id"), {"id": noise_id}
        )
        assert int(noise_exists.scalar() or 0) == 0
        lab_exists = await session.execute(
            text("SELECT COUNT(*) FROM comments WHERE id=:id"), {"id": lab_id}
        )
        assert int(lab_exists.scalar() or 0) == 1

        noise_labels = await session.execute(
            text(
                "SELECT COUNT(*) FROM content_labels WHERE content_type='comment' AND content_id=:id"
            ),
            {"id": noise_id},
        )
        assert int(noise_labels.scalar() or 0) == 0
        noise_entities = await session.execute(
            text(
                "SELECT COUNT(*) FROM content_entities WHERE content_type='comment' AND content_id=:id"
            ),
            {"id": noise_id},
        )
        assert int(noise_entities.scalar() or 0) == 0

        lab_labels = await session.execute(
            text(
                "SELECT COUNT(*) FROM content_labels WHERE content_type='comment' AND content_id=:id"
            ),
            {"id": lab_id},
        )
        assert int(lab_labels.scalar() or 0) == 1
        lab_entities = await session.execute(
            text(
                "SELECT COUNT(*) FROM content_entities WHERE content_type='comment' AND content_id=:id"
            ),
            {"id": lab_id},
        )
        assert int(lab_entities.scalar() or 0) == 1
