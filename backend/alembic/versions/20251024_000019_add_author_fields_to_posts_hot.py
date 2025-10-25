"""add author fields to posts_hot"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251024_000019"
down_revision = "20251024_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts_hot",
        sa.Column("author_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "posts_hot",
        sa.Column("author_name", sa.String(length=100), nullable=True),
    )
    op.execute(
        """
        UPDATE posts_hot
        SET
            author_name = COALESCE(author_name, metadata->>'author'),
            author_id = COALESCE(author_id, metadata->>'author')
        """
    )


def downgrade() -> None:
    op.drop_column("posts_hot", "author_name")
    op.drop_column("posts_hot", "author_id")
