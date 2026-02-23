"""add_l1_secondary_to_post_semantic_labels

Revision ID: 10e971cacbb4
Revises: 20251206_100001
Create Date: 2025-12-07 10:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10e971cacbb4'
down_revision = '20251206_100001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.add_column('post_semantic_labels', sa.Column('l1_secondary', sa.String(length=50), nullable=True))
    # op.create_index('idx_psl_l1_sec', 'post_semantic_labels', ['l1_secondary'], unique=False)
    pass


def downgrade() -> None:
    op.drop_index('idx_psl_l1_sec', table_name='post_semantic_labels')
    op.drop_column('post_semantic_labels', 'l1_secondary')