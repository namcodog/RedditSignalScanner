"""Add DecisionUnit fields to insight_cards and enhance evidences.

DecisionUnit storage strategy (Phase107):
- Reuse insight_cards as the physical table.
- Add kind + du_payload and a few indexed columns.
- Provide a stable read surface via decision_units_v view.

Revision ID: 20260103_000002
Revises: 20260103_000001
Create Date: 2026-01-03
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260103_000002"
down_revision: str | None = "20260103_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _relation_exists(name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
    return result.scalar() is not None


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name LIMIT 1"),
        {"name": name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _relation_exists("insight_cards"):
        return

    op.add_column(
        "insight_cards",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'insight'"),
        ),
    )
    op.add_column(
        "insight_cards",
        sa.Column("concept_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "insight_cards",
        sa.Column("signal_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "insight_cards",
        sa.Column("du_schema_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "insight_cards",
        sa.Column(
            "du_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    if _relation_exists("semantic_concepts"):
        op.create_foreign_key(
            "fk_insight_cards_concept_id_semantic_concepts",
            "insight_cards",
            "semantic_concepts",
            ["concept_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Allow DecisionUnit to reuse the same title as a legacy insight card under the same task.
    if _constraint_exists("uq_insight_cards_task_title"):
        op.drop_constraint("uq_insight_cards_task_title", "insight_cards", type_="unique")
    op.create_unique_constraint(
        "uq_insight_cards_task_kind_title",
        "insight_cards",
        ["task_id", "kind", "title"],
    )

    op.create_index(
        "idx_insight_cards_kind_created_at",
        "insight_cards",
        ["kind", "created_at"],
    )
    op.create_index(
        "idx_insight_cards_task_kind_created_at",
        "insight_cards",
        ["task_id", "kind", "created_at"],
    )
    op.create_index(
        "idx_insight_cards_concept_kind_created_at",
        "insight_cards",
        ["concept_id", "kind", "created_at"],
    )
    op.create_index(
        "idx_insight_cards_signal_kind_created_at",
        "insight_cards",
        ["signal_type", "kind", "created_at"],
    )
    op.create_index(
        "idx_insight_cards_du_payload_gin",
        "insight_cards",
        ["du_payload"],
        postgresql_using="gin",
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW decision_units_v AS
        SELECT
            id,
            task_id,
            title,
            summary,
            confidence,
            time_window_days,
            subreddits,
            concept_id,
            signal_type,
            du_schema_version,
            du_payload,
            created_at,
            updated_at
        FROM insight_cards
        WHERE kind = 'decision_unit';
        """
    )

    # Evidence: add stable internal content refs (post/comment id). Keep nullable for backwards compatibility.
    if _relation_exists("evidences"):
        op.add_column(
            "evidences",
            sa.Column("content_type", sa.String(length=16), nullable=True),
        )
        op.add_column(
            "evidences",
            sa.Column("content_id", sa.BigInteger(), nullable=True),
        )
        op.create_index(
            "idx_evidences_content_ref",
            "evidences",
            ["content_type", "content_id"],
        )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS decision_units_v")

    if _relation_exists("evidences"):
        op.drop_index("idx_evidences_content_ref", table_name="evidences")
        op.drop_column("evidences", "content_id")
        op.drop_column("evidences", "content_type")

    if not _relation_exists("insight_cards"):
        return

    op.drop_index("idx_insight_cards_du_payload_gin", table_name="insight_cards")
    op.drop_index("idx_insight_cards_signal_kind_created_at", table_name="insight_cards")
    op.drop_index("idx_insight_cards_concept_kind_created_at", table_name="insight_cards")
    op.drop_index("idx_insight_cards_task_kind_created_at", table_name="insight_cards")
    op.drop_index("idx_insight_cards_kind_created_at", table_name="insight_cards")

    if _constraint_exists("uq_insight_cards_task_kind_title"):
        op.drop_constraint("uq_insight_cards_task_kind_title", "insight_cards", type_="unique")
    op.create_unique_constraint(
        "uq_insight_cards_task_title",
        "insight_cards",
        ["task_id", "title"],
    )

    if _constraint_exists("fk_insight_cards_concept_id_semantic_concepts"):
        op.drop_constraint(
            "fk_insight_cards_concept_id_semantic_concepts",
            "insight_cards",
            type_="foreignkey",
        )

    op.drop_column("insight_cards", "du_payload")
    op.drop_column("insight_cards", "du_schema_version")
    op.drop_column("insight_cards", "signal_type")
    op.drop_column("insight_cards", "concept_id")
    op.drop_column("insight_cards", "kind")

