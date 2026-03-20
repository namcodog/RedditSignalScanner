from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.report_repository import ReportRepository
from app.schemas.analysis import AnalysisRead, CommunitySourceDetail
from app.schemas.report_payload import ReportOverview, ReportPayload, ReportStats
from app.services.report.report_request_workflow import (
    ReportRequestWorkflowInput,
    run_report_request_workflow,
)
from app.services.report.report_runtime import ReportRuntime

try:  # Optional import for controlled summary (Spec 011)
    from app.services.report.controlled_generator import build_context as _cg_build_ctx, render_report as _cg_render
except Exception:  # pragma: no cover - keep service resilient if module unavailable
    _cg_build_ctx = None  # type: ignore
    _cg_render = None  # type: ignore


class ReportServiceError(Exception):
    """Base class for service-layer errors."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ReportNotFoundError(ReportServiceError):
    status_code = 404


class ReportAccessDeniedError(ReportServiceError):
    status_code = 403


class ReportNotReadyError(ReportServiceError):
    status_code = 409


class ReportDataValidationError(ReportServiceError):
    status_code = 500


@dataclass(slots=True)
class ReportServiceConfig:
    community_members: dict[str, int]
    cache_ttl_seconds: int
    target_analysis_version: str


class ReportCacheProtocol(Protocol):
    async def get(self, key: str) -> ReportPayload | None:
        ...

    async def set(self, key: str, value: ReportPayload) -> None:
        ...

    async def invalidate(self, key: str) -> None:
        ...


class InMemoryReportCache(ReportCacheProtocol):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = max(1, ttl_seconds)
        self._store: dict[str, tuple[float, ReportPayload]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ReportPayload | None:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at <= time.monotonic():
                self._store.pop(key, None)
                return None
            return payload.model_copy(deep=True)

    async def set(self, key: str, value: ReportPayload) -> None:
        async with self._lock:
            self._store[key] = (
                time.monotonic() + self._ttl_seconds,
                value.model_copy(deep=True),
            )

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class ReportService:
    """Business logic for assembling the report analysis payload."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        config: ReportServiceConfig | None = None,
        cache: ReportCacheProtocol | None = None,
        repository: ReportRepository | None = None,
    ) -> None:
        resolved_config = config or ReportServiceConfig(
            community_members=settings.report_community_members,
            cache_ttl_seconds=settings.report_cache_ttl_seconds,
            target_analysis_version=settings.report_target_analysis_version,
        )
        self._config = resolved_config
        self._repository = repository or ReportRepository(db)
        self._cache = cache or InMemoryReportCache(resolved_config.cache_ttl_seconds)
        self._runtime = ReportRuntime(
            db=db,
            repository=self._repository,
            config=resolved_config,
            cache_get=self._cache.get if self._cache else None,
            cache_set=self._cache.set if self._cache else None,
            controlled_build_context=_cg_build_ctx,
            controlled_render_report=_cg_render,
        )

    async def get_report(self, task_id: UUID, user_id: UUID) -> ReportPayload:
        from app.core.config import settings as _cfg
        result = await run_report_request_workflow(
            workflow_input=ReportRequestWorkflowInput(
                task_id=task_id,
                user_id=user_id,
                inline_llm_enabled=bool(
                    getattr(_cfg, "enable_report_inline_llm", False)
                ),
            ),
            deps=self._runtime.build_request_workflow_deps(
                not_found_error=ReportNotFoundError,
                access_denied_error=ReportAccessDeniedError,
                not_ready_error=ReportNotReadyError,
                validation_error=ReportDataValidationError,
                validate_analysis_payload=self.validate_analysis_payload,
                fetch_member_count=self.fetch_community_member_count,
                coerce_report_html=self.coerce_report_html,
            ),
        )
        return result.payload

    @property
    def runtime(self) -> ReportRuntime:
        return self._runtime

    def validate_analysis_payload(self, analysis: Any) -> AnalysisRead:
        return self._runtime.validate_analysis_payload(
            analysis,
            error_cls=ReportDataValidationError,
        )

    async def fetch_community_member_count(self, community_name: str) -> int:
        return await self._runtime.fetch_community_member_count(community_name)

    async def build_overview(
        self,
        communities_detail: list[CommunitySourceDetail],
        stats: ReportStats,
    ) -> ReportOverview:
        return await self._runtime.build_overview(communities_detail, stats)

    @staticmethod
    def coerce_report_html(raw: str | None) -> str:
        return ReportRuntime.coerce_report_html(raw)

    @staticmethod
    def format_analysis_version(version: Any) -> str:
        return ReportRuntime.format_analysis_version(version)


__all__ = [
    "InMemoryReportCache",
    "ReportAccessDeniedError",
    "ReportCacheProtocol",
    "ReportDataValidationError",
    "ReportNotFoundError",
    "ReportNotReadyError",
    "ReportService",
    "ReportServiceConfig",
    "ReportServiceError",
]
