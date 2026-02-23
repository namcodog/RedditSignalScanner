"""add example library table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8d5f0f1c2a3b"
down_revision = "ef9a716b7384"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "example_library",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("analysis_insights", sa.JSON(), nullable=False),
        sa.Column("analysis_sources", sa.JSON(), nullable=False),
        sa.Column("analysis_action_items", sa.JSON(), nullable=True),
        sa.Column("analysis_confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("analysis_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("report_html", sa.Text(), nullable=False),
        sa.Column("report_template_version", sa.String(length=10), nullable=False, server_default="1.0"),
        sa.Column("source_task_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_example_library")),
    )
    op.create_index(op.f("ix_example_library_active"), "example_library", ["is_active"], unique=False)
    op.create_index(op.f("ix_example_library_updated_at"), "example_library", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_example_library_updated_at"), table_name="example_library")
    op.drop_index(op.f("ix_example_library_active"), table_name="example_library")
    op.drop_table("example_library")
