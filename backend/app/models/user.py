from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk_column


class User(TimestampMixin, Base):
    """User account ensuring multi-tenant separation from day one."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="ck_users_valid_email",
        ),
        Index("idx_users_email", "email"),
        Index("idx_users_active", "is_active", postgresql_where=text("is_active = true")),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"User(id={self.id!s}, email={self.email!r}, is_active={self.is_active})"
