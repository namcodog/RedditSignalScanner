"""add comments and semantic tables

Revision ID: 20251112_000025
Revises: 34a283ef7d4e
Create Date: 2025-11-12 23:59:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251112_000025"
down_revision = "34a283ef7d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("reddit_comment_id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default=sa.text("'reddit'")),
        sa.Column("source_post_id", sa.String(length=100), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.String(length=32), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", sa.String(length=100), nullable=True),
        sa.Column("author_name", sa.String(length=100), nullable=True),
        sa.Column("author_created_utc", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_utc", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_submitter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("distinguished", sa.String(length=32), nullable=True),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("permalink", sa.Text(), nullable=True),
        sa.Column("removed_by_category", sa.String(length=64), nullable=True),
        sa.Column("awards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("reddit_comment_id", name="uq_comments_reddit_comment_id"),
        sa.CheckConstraint("depth >= 0", name="ck_comments_depth_non_negative"),
    )
    op.create_index(
        "idx_comments_post_time",
        "comments",
        ["source", "source_post_id", "created_utc"],
    )
    op.create_index(
        "idx_comments_subreddit_time",
        "comments",
        ["subreddit", "created_utc"],
    )

    # enums (string-based, native_enum=False)
    content_type = sa.Enum(
        "post", "comment", name="content_type", native_enum=False
    )
    content_category = sa.Enum(
        "pain", "solution", "other", name="content_category", native_enum=False
    )
    content_aspect = sa.Enum(
        "price",
        "subscription",
        "content",
        "install",
        "ecosystem",
        "strength",
        "other",
        name="content_aspect",
        native_enum=False,
    )
    entity_type = sa.Enum(
        "brand", "feature", "platform", "other", name="entity_type", native_enum=False
    )

    # content_labels
    op.create_table(
        "content_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("content_id", sa.BigInteger(), nullable=False),
        sa.Column("category", content_category, nullable=False),
        sa.Column("aspect", content_aspect, nullable=False, server_default=sa.text("'other'")),
        sa.Column("confidence", sa.Integer(), nullable=True),
    )
    op.create_index(
        "idx_content_labels_target",
        "content_labels",
        ["content_type", "content_id"],
    )
    op.create_index(
        "idx_content_labels_cat_aspect",
        "content_labels",
        ["category", "aspect"],
    )

    # content_entities
    op.create_table(
        "content_entities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("content_id", sa.BigInteger(), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False, server_default=sa.text("'other'")),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index(
        "idx_content_entities_target",
        "content_entities",
        ["content_type", "content_id"],
    )
    op.create_index(
        "idx_content_entities_entity",
        "content_entities",
        ["entity", "entity_type"],
    )


def downgrade() -> None:
    # drop in reverse order
    op.drop_index("idx_content_entities_entity", table_name="content_entities")
    op.drop_index("idx_content_entities_target", table_name="content_entities")
    op.drop_table("content_entities")

    op.drop_index("idx_content_labels_cat_aspect", table_name="content_labels")
    op.drop_index("idx_content_labels_target", table_name="content_labels")
    op.drop_table("content_labels")

    op.drop_index("idx_comments_subreddit_time", table_name="comments")
    op.drop_index("idx_comments_post_time", table_name="comments")
    op.drop_table("comments")

