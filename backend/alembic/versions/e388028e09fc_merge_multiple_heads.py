"""merge multiple heads"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e388028e09fc"
down_revision = ('20251026_000023', 'ef9a716b7384')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
