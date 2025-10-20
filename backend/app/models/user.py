from __future__ import annotations

import uuid

from enum import Enum
from typing import Optional

from sqlalchemy import CheckConstraint, Enum as SQLEnum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk_column


class MembershipLevel(str, Enum):
    """Enumerated membership tiers available to end users."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    @classmethod
    def ensure(cls, value: Optional[str | "MembershipLevel"]) -> "MembershipLevel":
        """Normalise arbitrary input into a valid membership level."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalised = value.strip().lower()
            for member in cls:
                if member.value == normalised:
                    return member
        return cls.FREE


class User(TimestampMixin, Base):
    """User account ensuring multi-tenant separation from day one."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="ck_users_valid_email",
        ),
        Index("idx_users_email", "email"),
        Index(
            "idx_users_active", "is_active", postgresql_where=text("is_active = true")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    membership_level: Mapped[MembershipLevel] = mapped_column(
        SQLEnum(
            MembershipLevel,
            name="membership_level_enum",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=MembershipLevel.FREE,
        server_default=MembershipLevel.FREE.value,
    )

    def __repr__(self) -> str:
        return (
            "User("
            f"id={self.id!s}, "
            f"email={self.email!r}, "
            f"is_active={self.is_active}, "
            f"membership_level={self.membership_level.value!r}"
            ")"
        )


__all__ = ["MembershipLevel", "User"]
