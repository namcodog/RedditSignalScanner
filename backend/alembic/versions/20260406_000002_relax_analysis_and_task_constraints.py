"""relax legacy analysis and terminal task constraints"""

from __future__ import annotations

from alembic import op


revision = "20260406_000002"
down_revision = "20260406_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE analyses DROP CONSTRAINT IF EXISTS ck_analyses_sources_schema")
    op.execute("ALTER TABLE analyses DROP CONSTRAINT IF EXISTS ck_analyses_ck_analyses_sources_schema")
    op.execute("ALTER TABLE analyses DROP CONSTRAINT IF EXISTS ck_analyses_insights_schema")
    op.execute("ALTER TABLE analyses DROP CONSTRAINT IF EXISTS ck_analyses_ck_analyses_insights_schema")
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_completed_status_alignment")
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_ck_tasks_completed_status_alignment")
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
    # Re-applying the legacy constraints can fail on valid modern report sources
    # and failed terminal tasks, so rollback leaves the relaxed contract intact.
    pass
