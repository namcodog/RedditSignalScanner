"""add membership_level to users

Revision ID: 20251020_000014
Revises: 20251019_000013
Create Date: 2025-10-20 07:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251020_000014'
down_revision = '20251019_000013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add membership_level column to users table."""
    # Add membership_level column with default value 'free'
    op.add_column(
        'users',
        sa.Column(
            'membership_level',
            sa.String(length=20),
            nullable=False,
            server_default='free'
        )
    )
    
    # Add check constraint to ensure valid membership levels
    op.create_check_constraint(
        'ck_users_membership_level',
        'users',
        "membership_level IN ('free', 'pro', 'enterprise')"
    )


def downgrade() -> None:
    """Remove membership_level column from users table."""
    op.drop_constraint('ck_users_membership_level', 'users', type_='check')
    op.drop_column('users', 'membership_level')

