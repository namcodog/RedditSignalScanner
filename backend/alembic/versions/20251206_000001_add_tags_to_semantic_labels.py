"""add tags array field to post_semantic_labels

用途：支持多维度标签（如 spam_ad, duplicate），与 l1_category 互补。
安全性：仅添加字段，不修改/删除现有数据。
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251206_000001"
down_revision = "20251204_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 tags 数组字段（可选，允许 NULL）
    op.add_column(
        "post_semantic_labels",
        sa.Column("tags", sa.ARRAY(sa.String(50)), nullable=True),
    )
    # 添加 GIN 索引支持数组查询
    op.create_index(
        "idx_psl_tags",
        "post_semantic_labels",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_psl_tags", table_name="post_semantic_labels")
    op.drop_column("post_semantic_labels", "tags")
