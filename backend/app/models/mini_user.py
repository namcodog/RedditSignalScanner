from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk_column


class MiniUser(TimestampMixin, Base):
    __tablename__ = "mini_users"

    id: Mapped[uuid.UUID] = uuid_pk_column()
    wx_openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    wx_unionid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False, server_default="探索者")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, server_default="free")
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MiniUserFavorite(Base):
    __tablename__ = "mini_user_favorites"
    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_mini_user_card"),)

    id: Mapped[uuid.UUID] = uuid_pk_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mini_users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = ["MiniUser", "MiniUserFavorite"]
