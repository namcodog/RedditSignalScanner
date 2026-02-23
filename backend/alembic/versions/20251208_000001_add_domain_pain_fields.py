"""add domain pain fields

Revision ID: 20251208_000001
Revises: 34a283ef7d4e
Create Date: 2025-12-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251208_000001'
down_revision = '20251205_000005'
# Let's check `alembic heads` or assume I need to find the real head.
# From list_dir, `6a1749ae0c7e_merge_rename_and_previous_heads.py` seems like a merge point.
# But `34a283ef7d4e` has specific name.
# Better to run `alembic revision` command to generate file, but I cannot interactive.
# I will use `run_command` to generate it.

branch_labels = None
depends_on = None

def upgrade():
    op.add_column('semantic_rules', sa.Column('domain', sa.String(length=50), nullable=True))
    op.add_column('semantic_rules', sa.Column('aspect', sa.String(length=50), nullable=True))
    op.add_column('semantic_rules', sa.Column('source', sa.String(length=20), server_default='yaml', nullable=True))
    op.create_index(op.f('ix_semantic_rules_domain'), 'semantic_rules', ['domain'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_semantic_rules_domain'), table_name='semantic_rules')
    op.drop_column('semantic_rules', 'source')
    op.drop_column('semantic_rules', 'aspect')
    op.drop_column('semantic_rules', 'domain')
