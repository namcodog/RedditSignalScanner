"""add blacklist fields to community_pool

Revision ID: 20251017_000007
Revises: 20251016_000006
Create Date: 2025-10-17 10:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251017_000007'
down_revision: Union[str, None] = '20251016_000006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add blacklist fields to community_pool
    op.add_column('community_pool', sa.Column('is_blacklisted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('community_pool', sa.Column('blacklist_reason', sa.String(length=255), nullable=True))
    op.add_column('community_pool', sa.Column('downrank_factor', sa.Numeric(precision=3, scale=2), nullable=True))


def downgrade() -> None:
    # Remove blacklist fields from community_pool
    op.drop_column('community_pool', 'downrank_factor')
    op.drop_column('community_pool', 'blacklist_reason')
    op.drop_column('community_pool', 'is_blacklisted')

