"""merge rename and previous heads"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "6a1749ae0c7e"
down_revision = ('20251027_000024', 'e388028e09fc')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
