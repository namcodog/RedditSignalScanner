from __future__ import annotations

import time
from collections import deque
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.schemas.analysis import CommunitySourceDetail
from app.schemas.community_export import CommunityExportResponse
from app.schemas.entity_export import EntityExportResponse
from app.schemas.report_payload import ReportPayload
from app.services.report.report_export_service import ExportFormat
from app.services.report.report_service import InMemoryReportCache


class SlidingWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max(1, max_requests)
        self._window_seconds = max(1, window_seconds)
        self._hits: dict[str, deque[float]] = {}

    def configure(self, *, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        if max_requests is not None:
            self._max_requests = max(1, max_requests)
        if window_seconds is not None:
            self._window_seconds = max(1, window_seconds)
        self._hits.clear()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits.setdefault(str(key), deque())
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


def _v1_reports():
    from app.api.v1.endpoints import reports as v1_reports

    return v1_reports


@router.options("/{task_id}")
async def options_analysis_report(task_id: str) -> Response:
    return await _v1_reports().options_analysis_report(task_id)


@router.get("/{task_id}", summary="Fetch completed analysis report", response_model=ReportPayload)
async def get_analysis_report(
    task_id: UUID,
    response: Response,
    payload: TokenPayload = Depends(decode_jwt_token),
    request: Request = None,
    db: AsyncSession = Depends(get_session),
) -> ReportPayload:
    del request  # legacy signature compatibility only
    return await _v1_reports().get_analysis_report(
        task_id=task_id,
        response=response,
        payload=payload,
        db=db,
    )


@router.get("/{task_id}/download", summary="Download report in specified format")
async def download_report(
    task_id: UUID,
    format: ExportFormat = Query("pdf", description="Export format: pdf|json|md"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return await _v1_reports().download_report(
        task_id=task_id,
        format=format,
        payload=payload,
        db=db,
    )


@router.get(
    "/{task_id}/communities",
    summary="Fetch full community list used in report",
    response_model=list[CommunitySourceDetail],
)
async def get_report_communities(
    task_id: UUID,
    response: Response,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> list[CommunitySourceDetail]:
    return await _v1_reports().get_report_communities(
        task_id=task_id,
        response=response,
        payload=payload,
        db=db,
    )


@router.get(
    "/{task_id}/entities/export",
    summary="Export entities list",
    response_model=EntityExportResponse,
)
async def export_entities(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> EntityExportResponse:
    return await _v1_reports().export_entities(
        task_id=task_id,
        payload=payload,
        db=db,
    )


@router.get(
    "/{task_id}/communities/export",
    summary="Export communities list (top or all)",
    response_model=CommunityExportResponse,
)
async def export_communities(
    task_id: UUID,
    scope: str = Query("all", pattern="^(top|all)$", description="导出范围：top 或 all"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> CommunityExportResponse:
    return await _v1_reports().export_communities(
        task_id=task_id,
        scope=scope,
        payload=payload,
        db=db,
    )


@router.get("/{task_id}/communities/download", summary="Download communities list as CSV")
async def download_communities(
    task_id: UUID,
    scope: str = Query("all", pattern="^(top|all)$", description="导出范围：top 或 all"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return await _v1_reports().download_communities(
        task_id=task_id,
        scope=scope,
        payload=payload,
        db=db,
    )


@router.get("/{task_id}/entities/download", summary="Download entities list as CSV")
async def download_entities(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return await _v1_reports().download_entities_csv(
        task_id=task_id,
        payload=payload,
        db=db,
    )


__all__ = ["router", "REPORT_RATE_LIMITER"]
