"""merge community import restore and cleanup branches"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "ef9a716b7384"
down_revision = ('103e8405c2e1', '20251024_000022')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
