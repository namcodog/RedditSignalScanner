"""create post_semantic_labels table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251204_000003"
down_revision = "20251203_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_semantic_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("post_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("l1_category", sa.String(length=50)),
        sa.Column("l2_business", sa.String(length=50)),
        sa.Column("l3_scene", sa.String(length=100)),
        sa.Column("matched_rule_ids", sa.ARRAY(sa.Integer())),
        sa.Column("top_terms", sa.ARRAY(sa.Text())),
        sa.Column("raw_scores", sa.JSON(), nullable=True),
        sa.Column("sentiment_score", sa.Float()),
        sa.Column("confidence", sa.Float()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts_raw.id"],
            name="fk_post_semantic_labels_post",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("idx_psl_l1", "post_semantic_labels", ["l1_category"])
    op.create_index("idx_psl_l2", "post_semantic_labels", ["l2_business"])
    op.create_index("idx_psl_sentiment", "post_semantic_labels", ["sentiment_score"])


def downgrade() -> None:
    op.drop_index("idx_psl_sentiment", table_name="post_semantic_labels")
    op.drop_index("idx_psl_l2", table_name="post_semantic_labels")
    op.drop_index("idx_psl_l1", table_name="post_semantic_labels")
    op.drop_table("post_semantic_labels")
