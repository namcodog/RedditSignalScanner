from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class SemanticAuditLog(TimestampMixin, Base):
    """语义库操作审计日志，记录所有变更。"""

    __tablename__ = "semantic_audit_logs"
    __table_args__ = (
        Index("ix_semantic_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_semantic_audit_logs_created_at", "created_at"),
        Index("ix_semantic_audit_logs_operator_id", "operator_id"),
        Index(
            "idx_semantic_audit_logs_changes_gin",
            "changes",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = int_pk_column()
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    changes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    operator_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = ["SemanticAuditLog"]

