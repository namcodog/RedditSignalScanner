"""add tracking fields to posts_raw and comments

Revision ID: 20251214_000004
Revises: 20251213_000002
Create Date: 2025-12-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251214_000004"
down_revision = "20251213_000002"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=:table AND column_name=:column
                LIMIT 1
                """
            ),
            {"table": table, "column": column},
        )
        return result.scalar() is not None
    except Exception:
        return False


def upgrade() -> None:
    # posts_raw: add tracking/meta fields
    if not _column_exists("posts_raw", "first_seen_at"):
        op.add_column(
            "posts_raw",
            sa.Column(
                "first_seen_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
        )
    if not _column_exists("posts_raw", "source_track"):
        op.add_column(
            "posts_raw",
            sa.Column(
                "source_track",
                sa.String(length=32),
                nullable=True,
                server_default=sa.text("'incremental'"),
            ),
        )
    if not _column_exists("posts_raw", "business_pool"):
        op.add_column(
            "posts_raw",
            sa.Column(
                "business_pool",
                sa.String(length=10),
                nullable=True,
                server_default=sa.text("'lab'"),
            ),
        )
    else:
        op.alter_column(
            "posts_raw",
            "business_pool",
            existing_type=sa.String(length=10),
            server_default=sa.text("'lab'"),
            existing_nullable=True,
        )
    op.create_index(
        "idx_posts_raw_source_track",
        "posts_raw",
        ["source_track"],
        unique=False,
    )

    # comments: add tracking/meta fields
    if not _column_exists("comments", "source_track"):
        op.add_column(
            "comments",
            sa.Column(
                "source_track",
                sa.String(length=32),
                nullable=True,
                server_default=sa.text("'incremental'"),
            ),
        )
    if not _column_exists("comments", "first_seen_at"):
        op.add_column(
            "comments",
            sa.Column(
                "first_seen_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
        )
    if not _column_exists("comments", "fetched_at"):
        op.add_column(
            "comments",
            sa.Column(
                "fetched_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
        )
    if not _column_exists("comments", "lang"):
        op.add_column(
            "comments",
            sa.Column("lang", sa.String(length=10), nullable=True),
        )
    if not _column_exists("comments", "business_pool"):
        op.add_column(
            "comments",
            sa.Column(
                "business_pool",
                sa.String(length=10),
                nullable=True,
                server_default=sa.text("'lab'"),
            ),
        )


def downgrade() -> None:
    # comments
    op.drop_column("comments", "business_pool")
    op.drop_column("comments", "lang")
    op.drop_column("comments", "fetched_at")
    op.drop_column("comments", "first_seen_at")
    op.drop_column("comments", "source_track")

    # posts_raw
    op.drop_index("idx_posts_raw_source_track", table_name="posts_raw")
    op.alter_column(
        "posts_raw",
        "business_pool",
        existing_type=sa.String(length=10),
        server_default=None,
        existing_nullable=True,
    )
    op.drop_column("posts_raw", "source_track")
    op.drop_column("posts_raw", "first_seen_at")
