"""add report timestamp columns"""

from __future__ import annotations

from alembic import op


revision = "20260406_000003"
down_revision = "20260406_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE reports
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        ALTER TABLE reports
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )


def downgrade() -> None:
    # Keep TimestampMixin columns on rollback to avoid breaking ORM-managed reports.
    pass
