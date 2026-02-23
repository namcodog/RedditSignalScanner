"""Add DecisionUnit feedback events (Phase107#5).

DecisionUnit feedback is append-only and must be able to answer:
- 谁在什么时候对哪条 DecisionUnit 做了什么评价？
- 这条评价对应哪条证据（evidence）？

Revision ID: 20260103_000003
Revises: 20260103_000002
Create Date: 2026-01-03
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260103_000003"
down_revision: str | None = "20260103_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_unit_feedback_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "decision_unit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="DecisionUnit ID（insight_cards.id, kind=decision_unit）",
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="冗余：DecisionUnit 所属 task_id（便于按 task 回放）",
        ),
        sa.Column(
            "topic_profile_id",
            sa.String(length=100),
            nullable=True,
            comment="可选：DecisionUnit 所属 task 的 topic_profile_id（用于运营复盘/聚合）",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="反馈者用户 ID",
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="可选：反馈关联的证据 ID（evidences.id）。缺省时由服务端选择 top evidence。",
        ),
        sa.Column(
            "label",
            sa.String(length=20),
            nullable=False,
            comment="反馈标签：correct/incorrect/mismatch/valuable/worthless",
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="可选：短备注",
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="可选：扩展信息（jsonb）",
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["decision_unit_id"],
            ["insight_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidences.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "label IN ('correct','incorrect','mismatch','valuable','worthless')",
            name="ck_decision_unit_feedback_events_label_valid",
        ),
    )

    op.create_index(
        "idx_du_feedback_decision_unit_id",
        "decision_unit_feedback_events",
        ["decision_unit_id"],
    )
    op.create_index(
        "idx_du_feedback_task_id",
        "decision_unit_feedback_events",
        ["task_id"],
    )
    op.create_index(
        "idx_du_feedback_user_id",
        "decision_unit_feedback_events",
        ["user_id"],
    )
    op.create_index(
        "idx_du_feedback_created_at",
        "decision_unit_feedback_events",
        ["created_at"],
    )
    op.create_index(
        "idx_du_feedback_du_created",
        "decision_unit_feedback_events",
        ["decision_unit_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_du_feedback_du_created", table_name="decision_unit_feedback_events")
    op.drop_index("idx_du_feedback_created_at", table_name="decision_unit_feedback_events")
    op.drop_index("idx_du_feedback_user_id", table_name="decision_unit_feedback_events")
    op.drop_index("idx_du_feedback_task_id", table_name="decision_unit_feedback_events")
    op.drop_index("idx_du_feedback_decision_unit_id", table_name="decision_unit_feedback_events")
    op.drop_table("decision_unit_feedback_events")

