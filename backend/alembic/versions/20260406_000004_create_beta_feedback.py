"""create beta feedback table"""

from __future__ import annotations

from alembic import op


revision = "20260406_000004"
down_revision = "20260406_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS beta_feedback (
            id UUID PRIMARY KEY,
            task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            satisfaction INTEGER NOT NULL,
            missing_communities VARCHAR[] NOT NULL DEFAULT '{}',
            comments TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_beta_feedback_satisfaction_range
                CHECK (satisfaction >= 1 AND satisfaction <= 5)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_beta_feedback_task_id ON beta_feedback(task_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_beta_feedback_user_id ON beta_feedback(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_beta_feedback_created_at ON beta_feedback(created_at)"
    )


def downgrade() -> None:
    # Keep user feedback data on rollback.
    pass
