"""Add task_outbox table + enqueue marker on crawler_run_targets (safe / additive).

Revision ID: 20251226_000008
Revises: 20251226_000007
Create Date: 2025-12-26

Why:
- Prevent "message sent but row missing" by using a transactional outbox.
- Track enqueue state on crawler_run_targets for idempotent dispatch.

Safety:
- Additive changes only.
- Indexes created CONCURRENTLY.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20251226_000008"
down_revision: str | None = "20251226_000007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name=:table
              AND column_name=:column
            LIMIT 1
            """
        ),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT to_regclass(:table)"),
        {"table": f"public.{table}"},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("crawler_run_targets", "enqueued_at"):
        op.add_column(
            "crawler_run_targets",
            sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("task_outbox"):
        op.create_table(
            "task_outbox",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("event_key", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column(
                "payload",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(length=20),
                server_default=sa.text("'pending'"),
                nullable=False,
            ),
            sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_task_outbox"),
            sa.UniqueConstraint("event_key", name="ux_task_outbox_event_key"),
        )

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_task_outbox_status_created_at
            ON task_outbox (status, created_at)
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_task_outbox_status_created_at")

    if _table_exists("task_outbox"):
        op.drop_table("task_outbox")

    if _column_exists("crawler_run_targets", "enqueued_at"):
        op.drop_column("crawler_run_targets", "enqueued_at")
