from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.tasks.maintenance_task import cleanup_soft_orphan_content_labels_entities_impl


@pytest.mark.asyncio
async def test_cleanup_soft_orphans_respects_retention_window() -> None:
    now = datetime.now(timezone.utc)
    old_cutoff = now - timedelta(days=45)
    recent_cutoff = now - timedelta(days=5)

    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE content_labels, content_entities, posts_hot, comments, posts_raw, community_pool "
                "RESTART IDENTITY CASCADE"
            )
        )

        community_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO community_pool
                        (
                            name, tier, categories, description_keywords, daily_posts, avg_comment_length,
                            user_feedback_count, discovered_count, is_active, created_at, updated_at,
                            priority, is_blacklisted, semantic_quality_score, health_status,
                            auto_tier_enabled
                        )
                    VALUES
                        (
                            'r/test', 'core', '[]'::jsonb, '{}'::jsonb, 0, 0,
                            0, 0, true, NOW(), NOW(),
                            'medium', false, 0.5, 'healthy',
                            true
                        )
                    RETURNING id
                    """
                )
            )
        ).scalar_one()

        post_raw_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO posts_raw
                        (
                            source, source_post_id, version, created_at, fetched_at, valid_from, is_current,
                            title, body, subreddit, community_id, author_name, is_duplicate
                        )
                    VALUES
                        (
                            'reddit', 'raw-soft-1', 1, :created_at, :created_at, :created_at, true,
                            'valid title long enough', 'valid body long enough', 'r/test', :community_id, 'tester', false
                        )
                    RETURNING id
                    """
                ),
                {"created_at": old_cutoff, "community_id": community_id},
            )
        ).scalar_one()

        post_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO posts_hot
                        (source, source_post_id, created_at, expires_at, title, body, subreddit)
                    VALUES
                        ('reddit', 'soft-post-1', :created_at, :expires_at, 't', NULL, 'r/test')
                    RETURNING id
                    """
                ),
                {"created_at": old_cutoff, "expires_at": old_cutoff},
            )
        ).scalar_one()

        comment_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO comments
                        (reddit_comment_id, source, source_post_id, subreddit, body, created_utc, removed_by_category, post_id)
                    VALUES
                        ('c-soft-1', 'reddit', 'p1', 'r/test', 'body', :created_utc, 'moderator', :post_id)
                    RETURNING id
                    """
                ),
                {"created_utc": old_cutoff, "post_id": post_raw_id},
            )
        ).scalar_one()

        await db.execute(
            text(
                """
                INSERT INTO content_labels
                    (content_type, content_id, category, aspect, confidence, created_at)
                VALUES
                    ('post', :post_id, 'pain', 'price', 80, :created_at),
                    ('comment', :comment_id, 'pain', 'price', 80, :created_at)
                """
            ),
            {"post_id": post_id, "comment_id": comment_id, "created_at": old_cutoff},
        )
        await db.execute(
            text(
                """
                INSERT INTO content_entities
                    (content_type, content_id, entity, entity_type, count, created_at)
                VALUES
                    ('post', :post_id, 'BrandX', 'brand', 1, :created_at),
                    ('comment', :comment_id, 'BrandY', 'brand', 1, :created_at)
                """
            ),
            {"post_id": post_id, "comment_id": comment_id, "created_at": old_cutoff},
        )

        recent_comment_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO comments
                        (reddit_comment_id, source, source_post_id, subreddit, body, created_utc, removed_by_category, post_id)
                    VALUES
                        ('c-soft-2', 'reddit', 'p2', 'r/test', 'body', :created_utc, 'moderator', :post_id)
                    RETURNING id
                    """
                ),
                {"created_utc": recent_cutoff, "post_id": post_raw_id},
            )
        ).scalar_one()
        await db.execute(
            text(
                """
                INSERT INTO content_labels
                    (content_type, content_id, category, aspect, confidence, created_at)
                VALUES
                    ('comment', :comment_id, 'pain', 'price', 80, :created_at)
                """
            ),
            {"comment_id": recent_comment_id, "created_at": recent_cutoff},
        )

        await db.commit()

    result = await cleanup_soft_orphan_content_labels_entities_impl(
        retention_days=30,
        batch_size=100,
        max_batches=10,
        lock_timeout_ms=1000,
        statement_timeout_s=5,
    )
    assert result["status"] == "completed"
    assert result["deleted_labels"] >= 2
    assert result["deleted_entities"] >= 2

    async with SessionFactory() as db:
        remaining = (
            await db.execute(
                text(
                    """
                    SELECT count(*)
                    FROM content_labels
                    WHERE content_id = :comment_id
                    """
                ),
                {"comment_id": recent_comment_id},
            )
        ).scalar_one()
        assert remaining == 1
