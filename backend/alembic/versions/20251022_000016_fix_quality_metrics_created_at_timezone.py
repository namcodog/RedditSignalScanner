"""fix quality_metrics created_at timezone

Revision ID: 20251022_000016
Revises: 20251021_000015
Create Date: 2025-10-22 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251022_000016'
down_revision: Union[str, None] = '20251021_000015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 修改 created_at 字段为 TIMESTAMP WITH TIME ZONE
    op.execute("""
        ALTER TABLE quality_metrics 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    # 回退为 TIMESTAMP WITHOUT TIME ZONE
    op.execute("""
        ALTER TABLE quality_metrics 
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

