"""add quality_metrics table

Revision ID: 20251021_000015
Revises: 20251020_000014
Create Date: 2025-10-21 14:00:00.000000

基于 speckit-006 User Story 1 (US1) - Task T005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251021_000015'
down_revision = '20251020_000014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create quality_metrics table."""
    op.create_table(
        'quality_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('collection_success_rate', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('deduplication_rate', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('processing_time_p50', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('processing_time_p95', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            'collection_success_rate BETWEEN 0.00 AND 1.00',
            name='ck_quality_metrics_collection_success_rate_range'
        ),
        sa.CheckConstraint(
            'deduplication_rate BETWEEN 0.00 AND 1.00',
            name='ck_quality_metrics_deduplication_rate_range'
        ),
        sa.CheckConstraint(
            'processing_time_p50 >= 0',
            name='ck_quality_metrics_processing_time_p50_non_negative'
        ),
        sa.CheckConstraint(
            'processing_time_p95 >= 0',
            name='ck_quality_metrics_processing_time_p95_non_negative'
        ),
        sa.CheckConstraint(
            'processing_time_p95 >= processing_time_p50',
            name='ck_quality_metrics_p95_gte_p50'
        ),
    )
    
    # Create unique index on date
    op.create_index(
        'idx_quality_metrics_date',
        'quality_metrics',
        ['date'],
        unique=True
    )


def downgrade() -> None:
    """Drop quality_metrics table."""
    op.drop_index('idx_quality_metrics_date', table_name='quality_metrics')
    op.drop_table('quality_metrics')

