"""ensure comments.expires_at exists even in drifted DBs

Revision ID: 20251114_000031
Revises: 20251114_000030
Create Date: 2025-11-14 19:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251114_000031"
down_revision = "20251114_000030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Be defensive: add column/index if missing
    op.execute(
        "ALTER TABLE IF EXISTS comments ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL"
    )
    try:
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_expires_at ON comments (expires_at)"
        )
    except Exception:
        pass


def downgrade() -> None:
    # No-op downgrade to avoid dropping columns in drifted environments
    pass

