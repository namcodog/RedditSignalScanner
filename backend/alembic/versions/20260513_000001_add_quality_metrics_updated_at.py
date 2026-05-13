"""add updated_at to quality_metrics"""

from __future__ import annotations

from alembic import op

revision = "20260513_000001"
down_revision = "20260406_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE quality_metrics
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE quality_metrics
        DROP COLUMN IF EXISTS updated_at
        """
    )
