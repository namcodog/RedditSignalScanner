"""add storage metrics table and archive workflow"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251024_000020"
down_revision = "20251024_000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "storage_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "collected_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("posts_raw_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "posts_raw_current", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("posts_hot_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "posts_hot_expired", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "unique_subreddits", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("total_versions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("dedup_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("notes", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "idx_storage_metrics_collected_at",
        "storage_metrics",
        ["collected_at"],
        unique=False,
    )

    op.create_table(
        "posts_archive",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="reddit"),
        sa.Column("source_post_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "archived_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "idx_posts_archive_source_post",
        "posts_archive",
        ["source", "source_post_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION archive_old_posts(days_to_keep INTEGER DEFAULT 90, batch_size INTEGER DEFAULT 1000)
        RETURNS INTEGER AS $$
        DECLARE
            archived_count INTEGER;
            cutoff TIMESTAMP WITH TIME ZONE;
        BEGIN
            cutoff := NOW() - (days_to_keep || ' days')::INTERVAL;

            WITH moved_rows AS (
                SELECT id
                FROM posts_raw
                WHERE created_at < cutoff
                  AND is_current = FALSE
                ORDER BY created_at
                LIMIT batch_size
            )
            INSERT INTO posts_archive (source, source_post_id, version, archived_at, payload)
            SELECT
                pr.source,
                pr.source_post_id,
                pr.version,
                NOW(),
                to_jsonb(pr)
            FROM posts_raw pr
            JOIN moved_rows mr ON pr.id = mr.id;

            GET DIAGNOSTICS archived_count = ROW_COUNT;
            RETURN archived_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_old_posts(days_to_keep INTEGER DEFAULT 90)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
            cutoff_date TIMESTAMP WITH TIME ZONE;
        BEGIN
            PERFORM archive_old_posts(days_to_keep, 5000);

            cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

            DELETE FROM posts_raw
            WHERE created_at < cutoff_date
              AND is_current = FALSE;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_posts(INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS archive_old_posts(INTEGER, INTEGER)")
    op.drop_index("idx_posts_archive_source_post", table_name="posts_archive")
    op.drop_table("posts_archive")
    op.drop_index("idx_storage_metrics_collected_at", table_name="storage_metrics")
    op.drop_table("storage_metrics")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_old_posts(days_to_keep INTEGER DEFAULT 90)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
            cutoff_date TIMESTAMP WITH TIME ZONE;
        BEGIN
            cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

            DELETE FROM posts_raw
            WHERE created_at < cutoff_date
              AND is_current = FALSE;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
