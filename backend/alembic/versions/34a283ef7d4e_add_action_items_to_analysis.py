"""add action_items to analysis

Revision ID: 34a283ef7d4e
Revises: 6a1749ae0c7e
Create Date: 2025-10-27 22:39:39.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '34a283ef7d4e'
down_revision = '6a1749ae0c7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add action_items JSONB column to analyses table."""
    op.add_column(
        'analyses',
        sa.Column('action_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Remove action_items column from analyses table."""
    op.drop_column('analyses', 'action_items')

