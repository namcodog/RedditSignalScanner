from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.schemas.analysis import AnalysisRead
from app.schemas.report_payload import ReportPayload
from app.services.report.report_runtime_factory import (
    ReportAssemblyDepsFactoryInput,
    ReportRequestDepsFactoryInput,
    build_report_assembly_deps,
    build_report_request_workflow_deps,
    default_membership_allowed,
)
from app.services.report.report_assembly_workflow import ReportAssemblyDeps
from app.services.report.report_runtime_helpers import (
    build_runtime_overview,
    coerce_runtime_report_html,
    fetch_runtime_community_member_count,
    format_runtime_analysis_version,
    is_market_mode_enabled,
    resolve_report_quality_level,
    validate_runtime_analysis_payload,
)
from app.services.report.report_request_workflow import ReportRequestWorkflowDeps

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportRuntime:
    db: Any
    repository: Any
    config: Any
    cache_get: Callable[[str], Awaitable[ReportPayload | None]] | None
    cache_set: Callable[[str, ReportPayload], Awaitable[None]] | None
    controlled_build_context: Callable[..., Any] | None
    controlled_render_report: Callable[..., Any] | None

    def quality_level(self) -> str:
        return resolve_report_quality_level()

    def is_market_mode_enabled(self) -> bool:
        return is_market_mode_enabled()

    def validate_analysis_payload(
        self,
        analysis: Any,
        *,
        error_cls: type[Exception],
    ) -> AnalysisRead:
        return validate_runtime_analysis_payload(
            analysis,
            target_analysis_version=self.config.target_analysis_version,
            error_cls=error_cls,
        )

    async def fetch_community_member_count(self, community_name: str) -> int:
        return await fetch_runtime_community_member_count(
            community_name,
            repository=self.repository,
            configured_member_counts=self.config.community_members,
        )

    async def build_overview(
        self,
        communities_detail: list[Any],
        stats: Any,
    ) -> Any:
        return await build_runtime_overview(
            communities_detail,
            stats,
            fetch_member_count=self.fetch_community_member_count,
        )

    @staticmethod
    def coerce_report_html(raw: str | None) -> str:
        return coerce_runtime_report_html(raw)

    @staticmethod
    def format_analysis_version(version: Any) -> str:
        return format_runtime_analysis_version(version)

    def build_assembly_deps(
        self,
        *,
        coerce_report_html: Callable[[str | None], str] | None = None,
        fetch_member_count: Callable[[str], Awaitable[int]] | None = None,
    ) -> ReportAssemblyDeps:
        resolved_fetch_member_count = fetch_member_count or self.fetch_community_member_count
        resolved_coerce_report_html = coerce_report_html or self.coerce_report_html
        return build_report_assembly_deps(
            ReportAssemblyDepsFactoryInput(
                db=self.db,
                quality_level=self.quality_level(),
                product_description=getattr(
                    settings,
                    "report_product_description",
                    "跨境电商支付解决方案",
                ),
                market_report_enabled=bool(
                    getattr(settings, "enable_market_report", False)
                ),
                prefer_market_report=self.is_market_mode_enabled(),
                enable_llm_summary=bool(
                    getattr(settings, "enable_llm_summary", True)
                ),
                llm_model_name=str(
                    getattr(settings, "llm_model_name", "local-extractive")
                ),
                openai_api_key=str(getattr(settings, "openai_api_key", "") or ""),
                controlled_build_context=self.controlled_build_context,
                controlled_render_report=self.controlled_render_report,
                coerce_report_html=resolved_coerce_report_html,
                fetch_member_count=resolved_fetch_member_count,
            )
        )

    def build_request_workflow_deps(
        self,
        *,
        not_found_error: type[Exception],
        access_denied_error: type[Exception],
        not_ready_error: type[Exception],
        validation_error: type[Exception],
        validate_analysis_payload: Callable[[Any], AnalysisRead] | None = None,
        fetch_member_count: Callable[[str], Awaitable[int]] | None = None,
        coerce_report_html: Callable[[str | None], str] | None = None,
    ) -> ReportRequestWorkflowDeps:
        prefer_market_report = self.is_market_mode_enabled()
        resolved_validate = validate_analysis_payload or (
            lambda analysis: self.validate_analysis_payload(
                analysis,
                error_cls=validation_error,
            )
        )
        return build_report_request_workflow_deps(
            ReportRequestDepsFactoryInput(
                load_task_with_analysis=self.repository.get_task_with_analysis,
                is_membership_allowed=default_membership_allowed,
                make_not_found_error=not_found_error,
                make_access_denied_error=access_denied_error,
                make_not_ready_error=not_ready_error,
                cache_get=self.cache_get,
                cache_set=self.cache_set,
                validate_analysis_payload=resolved_validate,
                assembly_deps=self.build_assembly_deps(
                    coerce_report_html=coerce_report_html,
                    fetch_member_count=fetch_member_count,
                ),
                prefer_market_report=prefer_market_report,
            )
        )


__all__ = [
    "ReportAssemblyDepsFactoryInput",
    "ReportRequestDepsFactoryInput",
    "ReportRuntime",
    "build_report_assembly_deps",
    "build_report_request_workflow_deps",
    "is_market_mode_enabled",
    "resolve_report_quality_level",
]
