"""add mini users and favorites"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260405_000001"
down_revision = "20260330_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mini_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wx_openid", sa.String(length=64), nullable=False),
        sa.Column("wx_unionid", sa.String(length=64), nullable=True),
        sa.Column("nickname", sa.String(length=64), server_default="探索者", nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("plan", sa.String(length=16), server_default="free", nullable=False),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mini_users")),
        sa.UniqueConstraint("wx_openid", name=op.f("uq_mini_users_wx_openid")),
    )
    op.create_index(op.f("ix_mini_users_wx_openid"), "mini_users", ["wx_openid"], unique=False)

    op.create_table(
        "mini_user_favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["mini_users.id"], name=op.f("fk_mini_user_favorites_user_id_mini_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mini_user_favorites")),
        sa.UniqueConstraint("user_id", "card_id", name="uq_mini_user_card"),
    )
    op.create_index(op.f("ix_mini_user_favorites_user_id"), "mini_user_favorites", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mini_user_favorites_user_id"), table_name="mini_user_favorites")
    op.drop_table("mini_user_favorites")
    op.drop_index(op.f("ix_mini_users_wx_openid"), table_name="mini_users")
    op.drop_table("mini_users")
