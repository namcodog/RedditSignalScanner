"""create semantic_concepts and semantic_rules"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251203_000002"
down_revision = "20251203_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_concepts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "semantic_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=20), nullable=False, server_default="keyword"),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["semantic_concepts.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("concept_id", "term", "rule_type", name="uq_semantic_rules_term_type"),
    )
    op.create_index("idx_semantic_rules_term", "semantic_rules", ["term"])
    op.create_index("idx_semantic_rules_concept", "semantic_rules", ["concept_id"])


def downgrade() -> None:
    op.drop_index("idx_semantic_rules_concept", table_name="semantic_rules")
    op.drop_index("idx_semantic_rules_term", table_name="semantic_rules")
    op.drop_table("semantic_rules")
    op.drop_table("semantic_concepts")
