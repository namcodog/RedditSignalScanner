"""Create quarantine and audit tables used by truth-source triggers."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260406_000005"
down_revision: str | None = "20260406_000004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS posts_quarantine (
            id BIGSERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL DEFAULT 'reddit',
            source_post_id VARCHAR(100) NOT NULL,
            subreddit VARCHAR(100),
            title TEXT,
            body TEXT,
            author_name VARCHAR(100),
            reject_reason TEXT NOT NULL,
            original_payload JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posts_quarantine_source_post_id
        ON posts_quarantine (source_post_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS data_audit_events (
            id BIGSERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            target_type VARCHAR(100) NOT NULL,
            target_id TEXT,
            old_value JSONB,
            new_value JSONB,
            reason TEXT,
            source_component VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_data_audit_events_target
        ON data_audit_events (target_type, target_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cleanup_logs (
            id BIGSERIAL PRIMARY KEY,
            executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            total_records_cleaned INTEGER NOT NULL DEFAULT 0,
            breakdown JSONB,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            success BOOLEAN NOT NULL DEFAULT true
        )
        """
    )


def downgrade() -> None:
    # Keep the tables: earlier truth-source triggers may still reference them.
    pass
