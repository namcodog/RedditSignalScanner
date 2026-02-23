from __future__ import annotations

from typing import Any, Mapping
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_audit_log import SemanticAuditLog


SensitiveKeys = {"password", "password_hash", "token", "access_token", "refresh_token", "secret", "api_key"}


def _sanitize_payload(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Remove obviously sensitive keys from nested payloads."""
    if payload is None:
        return None

    def _sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: _sanitize(v)
                for k, v in value.items()
                if k not in SensitiveKeys
            }
        if isinstance(value, list):
            return [_sanitize(v) for v in value]
        return value

    return _sanitize(dict(payload))


class SemanticAuditLogger:
    """Async helper for writing semantic audit logs.

    This helper is intentionally lightweight: it never commits transactions,
    leaving lifecycle control to the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _log(
        self,
        action: str,
        entity_type: str,
        entity_id: int,
        changes: Mapping[str, Any] | None,
        operator_id: uuid.UUID | None = None,
        operator_ip: str | None = None,
        reason: str | None = None,
    ) -> SemanticAuditLog:
        entry = SemanticAuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=_sanitize_payload(changes),
            operator_id=operator_id,
            operator_ip=operator_ip,
            reason=reason,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def log_create(
        self,
        entity_type: str,
        entity_id: int,
        after: Mapping[str, Any],
        operator_id: uuid.UUID | None = None,
        operator_ip: str | None = None,
    ) -> SemanticAuditLog:
        """Log creation of a new semantic entity."""
        return await self._log(
            action="create",
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"before": None, "after": after},
            operator_id=operator_id,
            operator_ip=operator_ip,
            reason=None,
        )

    async def log_update(
        self,
        entity_type: str,
        entity_id: int,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        operator_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> SemanticAuditLog:
        """Log an update operation with before/after snapshots."""
        return await self._log(
            action="update",
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"before": before, "after": after},
            operator_id=operator_id,
            operator_ip=None,
            reason=reason,
        )

    async def log_approve(
        self,
        candidate_id: int,
        operator_id: uuid.UUID | None,
        category: str,
        layer: str,
    ) -> SemanticAuditLog:
        """Log approval of a semantic candidate."""
        return await self._log(
            action="approve",
            entity_type="semantic_candidate",
            entity_id=candidate_id,
            changes={
                "before": {"status": "pending"},
                "after": {"status": "approved", "category": category, "layer": layer},
            },
            operator_id=operator_id,
            operator_ip=None,
            reason=None,
        )

    async def log_reject(
        self,
        candidate_id: int,
        operator_id: uuid.UUID | None,
        reason: str,
    ) -> SemanticAuditLog:
        """Log rejection of a semantic candidate."""
        return await self._log(
            action="reject",
            entity_type="semantic_candidate",
            entity_id=candidate_id,
            changes={
                "before": {"status": "pending"},
                "after": {"status": "rejected"},
            },
            operator_id=operator_id,
            operator_ip=None,
            reason=reason,
        )


__all__ = ["SemanticAuditLogger"]

