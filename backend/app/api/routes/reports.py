from __future__ import annotations

import asyncio
import time
from collections import deque
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.schemas.report_payload import ReportPayload
from app.services.report_service import (
    InMemoryReportCache,
    ReportAccessDeniedError,
    ReportDataValidationError,
    ReportNotFoundError,
    ReportNotReadyError,
    ReportService,
    ReportServiceError,
)

class SlidingWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max(1, max_requests)
        self._window_seconds = max(1, window_seconds)
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    def configure(self, *, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        if max_requests is not None:
            self._max_requests = max(1, max_requests)
        if window_seconds is not None:
            self._window_seconds = max(1, window_seconds)

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - self._window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


router = APIRouter(prefix="/report", tags=["analysis"])

REPORT_CACHE = InMemoryReportCache(settings.report_cache_ttl_seconds)
REPORT_RATE_LIMITER = SlidingWindowRateLimiter(
    max_requests=settings.report_rate_limit_per_minute,
    window_seconds=settings.report_rate_limit_window_seconds,
)


@router.options("/{task_id}")
async def options_analysis_report(task_id: str) -> Response:
    # CORS 预检请求在路由层直接放行，避免触发认证依赖
    return Response(status_code=204)

@router.get("/{task_id}", summary="Fetch completed analysis report", response_model=ReportPayload)
async def get_analysis_report(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> ReportPayload:
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    allowed = await REPORT_RATE_LIMITER.allow(payload.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    try:
        return await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


__all__ = ["router", "REPORT_RATE_LIMITER"]
