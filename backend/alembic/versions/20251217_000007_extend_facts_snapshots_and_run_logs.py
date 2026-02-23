"""extend facts_snapshots metadata + add facts_run_logs

Revision ID: 20251217_000007
Revises: 20251217_000006
Create Date: 2025-12-17
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20251217_000007"
down_revision: str | None = "20251217_000006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("facts_snapshots", sa.Column("audit_level", sa.String(length=20), nullable=True))
    op.add_column("facts_snapshots", sa.Column("status", sa.String(length=20), nullable=True))
    op.add_column(
        "facts_snapshots", sa.Column("validator_level", sa.String(length=10), nullable=True)
    )
    op.add_column("facts_snapshots", sa.Column("retention_days", sa.Integer(), nullable=True))
    op.add_column(
        "facts_snapshots", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "facts_snapshots", sa.Column("blocked_reason", sa.String(length=120), nullable=True)
    )
    op.add_column("facts_snapshots", sa.Column("error_code", sa.String(length=120), nullable=True))

    # Backfill audit_level based on task snapshot
    op.execute(
        """
        UPDATE facts_snapshots fs
        SET audit_level = COALESCE(
            t.audit_level,
            CASE
                WHEN t.topic_profile_id IS NOT NULL AND t.topic_profile_id <> '' THEN 'gold'
                ELSE 'lab'
            END
        )
        FROM tasks t
        WHERE fs.task_id = t.id
          AND fs.audit_level IS NULL
        """
    )
    op.execute("UPDATE facts_snapshots SET audit_level='lab' WHERE audit_level IS NULL")

    # Backfill status/tier defaults
    op.execute(
        """
        UPDATE facts_snapshots
        SET status = CASE
            WHEN tier = 'X_blocked' THEN 'blocked'
            ELSE 'ok'
        END
        WHERE status IS NULL
        """
    )
    op.execute(
        "UPDATE facts_snapshots SET validator_level='info' WHERE validator_level IS NULL"
    )
    op.execute(
        """
        UPDATE facts_snapshots
        SET retention_days = CASE audit_level
            WHEN 'gold' THEN 90
            WHEN 'noise' THEN 7
            ELSE 30
        END
        WHERE retention_days IS NULL
        """
    )
    op.execute(
        """
        UPDATE facts_snapshots
        SET expires_at = created_at + (retention_days || ' days')::interval
        WHERE expires_at IS NULL AND retention_days IS NOT NULL
        """
    )

    op.alter_column(
        "facts_snapshots",
        "audit_level",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'lab'"),
    )
    op.alter_column(
        "facts_snapshots",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'ok'"),
    )
    op.alter_column(
        "facts_snapshots",
        "validator_level",
        existing_type=sa.String(length=10),
        nullable=False,
        server_default=sa.text("'info'"),
    )
    op.alter_column(
        "facts_snapshots",
        "retention_days",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("30"),
    )

    op.create_check_constraint(
        "ck_facts_snapshots_valid_audit_level",
        "facts_snapshots",
        "audit_level IN ('gold','lab','noise')",
    )
    op.create_check_constraint(
        "ck_facts_snapshots_valid_status",
        "facts_snapshots",
        "status IN ('ok','blocked','failed')",
    )
    op.create_check_constraint(
        "ck_facts_snapshots_valid_validator_level",
        "facts_snapshots",
        "validator_level IN ('info','warn','error')",
    )
    op.create_index("idx_facts_snapshots_audit_level", "facts_snapshots", ["audit_level"])
    op.create_index("idx_facts_snapshots_status", "facts_snapshots", ["status"])
    op.create_index("idx_facts_snapshots_expires_at", "facts_snapshots", ["expires_at"])

    op.create_table(
        "facts_run_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False, comment="关联的分析任务 ID"),
        sa.Column(
            "audit_level",
            sa.String(length=20),
            nullable=False,
            server_default="lab",
            comment="审计档位：gold/lab/noise",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ok",
            comment="运行状态：ok/blocked/failed/skipped",
        ),
        sa.Column(
            "validator_level",
            sa.String(length=10),
            nullable=False,
            server_default="info",
            comment="validator 级别：info/warn/error",
        ),
        sa.Column(
            "retention_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
            comment="日志保留天数（默认 7 天）",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="日志过期时间（UTC）",
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="最小运行摘要（计数/配置/范围等）",
        ),
        sa.Column("error_code", sa.String(length=120), nullable=True, comment="失败/拦截错误码"),
        sa.Column("error_message_short", sa.Text(), nullable=True, comment="一行错误摘要"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "audit_level IN ('gold','lab','noise')",
            name="ck_facts_run_logs_valid_audit_level",
        ),
        sa.CheckConstraint(
            "status IN ('ok','blocked','failed','skipped')",
            name="ck_facts_run_logs_valid_status",
        ),
        sa.CheckConstraint(
            "validator_level IN ('info','warn','error')",
            name="ck_facts_run_logs_valid_validator_level",
        ),
    )
    op.create_index("idx_facts_run_logs_task_id", "facts_run_logs", ["task_id"])
    op.create_index("idx_facts_run_logs_created_at", "facts_run_logs", ["created_at"])
    op.create_index("idx_facts_run_logs_expires_at", "facts_run_logs", ["expires_at"])
    op.create_index("idx_facts_run_logs_audit_level", "facts_run_logs", ["audit_level"])
    op.create_index("idx_facts_run_logs_status", "facts_run_logs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_facts_run_logs_status", table_name="facts_run_logs")
    op.drop_index("idx_facts_run_logs_audit_level", table_name="facts_run_logs")
    op.drop_index("idx_facts_run_logs_expires_at", table_name="facts_run_logs")
    op.drop_index("idx_facts_run_logs_created_at", table_name="facts_run_logs")
    op.drop_index("idx_facts_run_logs_task_id", table_name="facts_run_logs")
    op.drop_table("facts_run_logs")

    op.drop_index("idx_facts_snapshots_expires_at", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_status", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_audit_level", table_name="facts_snapshots")
    op.drop_constraint(
        "ck_facts_snapshots_valid_validator_level",
        "facts_snapshots",
        type_="check",
    )
    op.drop_constraint(
        "ck_facts_snapshots_valid_status",
        "facts_snapshots",
        type_="check",
    )
    op.drop_constraint(
        "ck_facts_snapshots_valid_audit_level",
        "facts_snapshots",
        type_="check",
    )
    op.drop_column("facts_snapshots", "error_code")
    op.drop_column("facts_snapshots", "blocked_reason")
    op.drop_column("facts_snapshots", "expires_at")
    op.drop_column("facts_snapshots", "retention_days")
    op.drop_column("facts_snapshots", "validator_level")
    op.drop_column("facts_snapshots", "status")
    op.drop_column("facts_snapshots", "audit_level")
