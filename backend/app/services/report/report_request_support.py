from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.report_payload import ReportPayload

logger = logging.getLogger(__name__)


async def resolve_cached_report_payload(
    *,
    cache_get: Callable[[str], Awaitable[ReportPayload | None]] | None,
    cache_key: str,
    generated_at: datetime | None,
    task_id: UUID,
) -> ReportPayload | None:
    if cache_get is None:
        return None
    cached = await cache_get(cache_key)
    if cached is not None and cached.generated_at == generated_at:
        logger.debug("Cache hit for report task %s", task_id)
        return cached
    return None


async def finalize_report_request(
    *,
    payload: ReportPayload,
    analysis: Any,
    cache_key: str,
    cache_set: Callable[[str, ReportPayload], Awaitable[None]] | None,
    persist_report_structured: Callable[[Any, dict[str, Any]], Awaitable[bool]] | None,
    task_id: UUID,
    task_status: Any,
) -> None:
    canonical_report = getattr(payload, "canonical_report_json", None)
    if persist_report_structured is not None and isinstance(canonical_report, dict):
        await persist_report_structured(analysis, canonical_report)

    logger.debug(
        "Generated report payload for task %s (status=%s)",
        task_id,
        task_status,
    )
    if cache_set is not None:
        await cache_set(cache_key, payload)


__all__ = [
    "finalize_report_request",
    "resolve_cached_report_payload",
]
