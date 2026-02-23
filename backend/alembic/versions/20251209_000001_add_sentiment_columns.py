"""add_sentiment_columns

Revision ID: 20251209_000001
Revises: 20251208_000001_add_domain_pain_fields
Create Date: 2025-12-09 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251209_000001'
down_revision = '20251208_000001'
branch_labels = None
depends_on = None


def upgrade():
    # Add sentiment columns to content_labels
    op.add_column('content_labels', sa.Column('sentiment_score', sa.Float(), nullable=True))
    op.add_column('content_labels', sa.Column('sentiment_label', sa.String(length=20), nullable=True))
    
    # Create index for sentiment analysis queries
    op.create_index('idx_content_labels_sentiment', 'content_labels', ['sentiment_score'], unique=False)


def downgrade():
    op.drop_index('idx_content_labels_sentiment', table_name='content_labels')
    op.drop_column('content_labels', 'sentiment_label')
    op.drop_column('content_labels', 'sentiment_score')
