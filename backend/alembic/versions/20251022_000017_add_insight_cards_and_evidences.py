"""add insight_cards and evidences tables

Revision ID: 20251022_000017
Revises: 20251022_000016
Create Date: 2025-10-22 15:30:00.000000

基于 speckit-006 User Story 2 (US2) - Task T010
创建洞察卡片和证据表，支持洞察卡片 v0 功能
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251022_000017'
down_revision = '20251022_000016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create insight_cards and evidences tables."""
    
    # Create insight_cards table
    op.create_table(
        'insight_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False, comment='洞察卡片标题'),
        sa.Column('summary', sa.Text(), nullable=False, comment='洞察摘要'),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False, comment='置信度分数 (0.0-1.0)'),
        sa.Column('time_window_days', sa.Integer(), nullable=False, server_default='30', comment='时间窗口（天数）'),
        sa.Column('subreddits', postgresql.ARRAY(sa.String(length=100)), nullable=False, server_default='{}', comment='相关子版块列表'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'title', name='uq_insight_cards_task_title'),
        sa.CheckConstraint(
            '(confidence >= 0.0) AND (confidence <= 1.0)',
            name='ck_insight_cards_confidence_range'
        ),
        sa.CheckConstraint(
            'time_window_days > 0',
            name='ck_insight_cards_time_window_positive'
        ),
    )
    
    # Create indexes for insight_cards
    op.create_index('idx_insight_cards_task_id', 'insight_cards', ['task_id'])
    op.create_index('idx_insight_cards_confidence', 'insight_cards', ['confidence'])
    op.create_index('idx_insight_cards_created_at', 'insight_cards', ['created_at'])
    op.create_index(
        'idx_insight_cards_subreddits_gin',
        'insight_cards',
        ['subreddits'],
        postgresql_using='gin'
    )
    
    # Create evidences table
    op.create_table(
        'evidences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insight_card_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_url', sa.String(length=500), nullable=False, comment='原帖 URL'),
        sa.Column('excerpt', sa.Text(), nullable=False, comment='摘录内容'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, comment='帖子时间戳'),
        sa.Column('subreddit', sa.String(length=100), nullable=False, comment='子版块名称'),
        sa.Column('score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0', comment='证据分数 (0.0-1.0)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['insight_card_id'], ['insight_cards.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            '(score >= 0.0) AND (score <= 1.0)',
            name='ck_evidences_score_range'
        ),
    )
    
    # Create indexes for evidences
    op.create_index('idx_evidences_insight_card_id', 'evidences', ['insight_card_id'])
    op.create_index('idx_evidences_score', 'evidences', ['score'])
    op.create_index('idx_evidences_timestamp', 'evidences', ['timestamp'])
    op.create_index('idx_evidences_subreddit', 'evidences', ['subreddit'])


def downgrade() -> None:
    """Drop insight_cards and evidences tables."""
    
    # Drop evidences table and its indexes
    op.drop_index('idx_evidences_subreddit', table_name='evidences')
    op.drop_index('idx_evidences_timestamp', table_name='evidences')
    op.drop_index('idx_evidences_score', table_name='evidences')
    op.drop_index('idx_evidences_insight_card_id', table_name='evidences')
    op.drop_table('evidences')
    
    # Drop insight_cards table and its indexes
    op.drop_index('idx_insight_cards_subreddits_gin', table_name='insight_cards')
    op.drop_index('idx_insight_cards_created_at', table_name='insight_cards')
    op.drop_index('idx_insight_cards_confidence', table_name='insight_cards')
    op.drop_index('idx_insight_cards_task_id', table_name='insight_cards')
    op.drop_table('insight_cards')

