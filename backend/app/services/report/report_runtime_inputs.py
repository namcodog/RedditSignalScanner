from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Optional, Any

from app.core.config import settings
from app.schemas.analysis import AnalysisRead
from app.schemas.report_payload import ReportPayload
from app.services.report.report_runtime_factory import (
    ReportAssemblyDepsFactoryInput,
    ReportRequestDepsFactoryInput,
    default_membership_allowed,
)
from app.services.report.report_llm_policy import (
    resolve_report_reasoning_model_name,
)


def build_runtime_assembly_factory_input(
    runtime: Any,
    *,
    coerce_report_html:Optional[ Callable[[str]Optional[], str]] = None,
    fetch_member_count:Optional[ Callable[[str], Awaitable[int]]] = None,
) -> ReportAssemblyDepsFactoryInput:
    resolved_fetch_member_count = fetch_member_count or runtime.fetch_community_member_count
    resolved_coerce_report_html = coerce_report_html or runtime.coerce_report_html
    fast_model_name = str(getattr(settings, "llm_model_name", "local-extractive"))
    return ReportAssemblyDepsFactoryInput(
        db=runtime.db,
        quality_level=runtime.quality_level(),
        product_description=getattr(
            settings,
            "report_product_description",
            "跨境电商支付解决方案",
        ),
        market_report_enabled=bool(
            getattr(settings, "enable_market_report", False)
        ),
        prefer_market_report=runtime.is_market_mode_enabled(),
        enable_llm_summary=bool(
            getattr(settings, "enable_llm_summary", True)
        ),
        llm_model_name=fast_model_name,
        reasoning_model_name=resolve_report_reasoning_model_name(
            fast_model_name=fast_model_name,
        ),
        openai_api_key=str(getattr(settings, "openai_api_key", "") or ""),
        controlled_build_context=runtime.controlled_build_context,
        controlled_render_report=runtime.controlled_render_report,
        coerce_report_html=resolved_coerce_report_html,
        fetch_member_count=resolved_fetch_member_count,
    )


def build_runtime_request_factory_input(
    runtime: Any,
    *,
    not_found_error: type[Exception],
    access_denied_error: type[Exception],
    not_ready_error: type[Exception],
    validation_error: type[Exception],
    validate_analysis_payload:Optional[ Callable[[Any], AnalysisRead]] = None,
    fetch_member_count:Optional[ Callable[[str], Awaitable[int]]] = None,
    coerce_report_html:Optional[ Callable[[str]Optional[], str]] = None,
) -> ReportRequestDepsFactoryInput:
    resolved_validate = validate_analysis_payload or (
        lambda analysis: runtime.validate_analysis_payload(
            analysis,
            error_cls=validation_error,
        )
    )
    return ReportRequestDepsFactoryInput(
        load_task_with_analysis=runtime.repository.get_task_with_analysis,
        persist_report_structured=runtime.repository.persist_report_structured,
        is_membership_allowed=default_membership_allowed,
        make_not_found_error=not_found_error,
        make_access_denied_error=access_denied_error,
        make_not_ready_error=not_ready_error,
        cache_get=runtime.cache_get,
        cache_set=runtime.cache_set,
        validate_analysis_payload=resolved_validate,
        assembly_deps=runtime.build_assembly_deps(
            coerce_report_html=coerce_report_html,
            fetch_member_count=fetch_member_count,
        ),
        prefer_market_report=runtime.is_market_mode_enabled(),
    )


__all__ = [
    "build_runtime_assembly_factory_input",
    "build_runtime_request_factory_input",
]
