"""relax failed task completion constraint"""

from __future__ import annotations

from alembic import op

revision = "20260513_000002"
down_revision = "20260512_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_completed_status_alignment"
    )
    op.execute(
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_ck_tasks_completed_status_alignment"
    )
    op.execute(
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_completion_consistency"
    )
    op.execute(
        """
        UPDATE tasks
        SET completed_at = COALESCE(updated_at, now())
        WHERE status::text = 'failed' AND completed_at IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE tasks
        ADD CONSTRAINT ck_tasks_completed_status_alignment
        CHECK (
            ((status::text = 'completed') AND completed_at IS NOT NULL) OR
            ((status::text = 'failed') AND completed_at IS NOT NULL) OR
            ((status::text NOT IN ('completed', 'failed')) AND completed_at IS NULL)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_completed_status_alignment"
    )
    op.execute(
        """
        ALTER TABLE tasks
        ADD CONSTRAINT ck_tasks_completed_status_alignment
        CHECK (
            ((status::text = 'completed') AND completed_at IS NOT NULL) OR
            ((status::text = 'failed') AND completed_at IS NOT NULL) OR
            ((status::text NOT IN ('completed', 'failed')) AND completed_at IS NULL)
        )
        """
    )
