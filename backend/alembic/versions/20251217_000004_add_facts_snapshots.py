"""Add facts_snapshots table (facts_v2 audit package)

Revision ID: 20251217_000004
Revises: 20251217_000003
Create Date: 2025-12-17 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20251217_000004"
down_revision: Union[str, None] = "20251217_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "facts_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False, comment="关联的分析任务 ID"),
        sa.Column(
            "schema_version",
            sa.String(length=10),
            nullable=False,
            server_default="2.0",
            comment="facts_v2 schema version",
        ),
        sa.Column(
            "v2_package",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="facts_v2 审计包（v2_package）",
        ),
        sa.Column(
            "quality",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="质量闸门结果（passed/tier/flags/metrics + 其它校验信息）",
        ),
        sa.Column(
            "passed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否通过质量闸门（tier != X_blocked）",
        ),
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="C_scouting",
            comment="报告等级：A_full/B_trimmed/C_scouting/X_blocked",
        ),
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
            "schema_version <> ''",
            name="ck_facts_snapshots_schema_version_non_empty",
        ),
        sa.CheckConstraint(
            "tier IN ('A_full','B_trimmed','C_scouting','X_blocked')",
            name="ck_facts_snapshots_valid_tier",
        ),
    )
    op.create_index("idx_facts_snapshots_task_id", "facts_snapshots", ["task_id"])
    op.create_index("idx_facts_snapshots_created_at", "facts_snapshots", ["created_at"])
    op.create_index(
        "idx_facts_snapshots_task_created",
        "facts_snapshots",
        ["task_id", "created_at"],
    )
    op.create_index("idx_facts_snapshots_tier", "facts_snapshots", ["tier"])
    op.create_index("idx_facts_snapshots_passed", "facts_snapshots", ["passed"])


def downgrade() -> None:
    op.drop_index("idx_facts_snapshots_passed", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_tier", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_task_created", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_created_at", table_name="facts_snapshots")
    op.drop_index("idx_facts_snapshots_task_id", table_name="facts_snapshots")
    op.drop_table("facts_snapshots")

