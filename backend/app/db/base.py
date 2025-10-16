from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base declarative class with sensible defaults."""

    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        }
    )


class TimestampMixin:
    """Shared timestamp columns using timezone-aware values."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def generate_uuid() -> uuid.UUID:
    """Return uuid4 value as callable default to avoid evaluation at import time."""
    return uuid.uuid4()


def uuid_pk_column() -> Mapped[uuid.UUID]:
    """Factory for UUID primary key columns."""
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
        nullable=False,
    )
