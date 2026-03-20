from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.models.user import MembershipLevel
from app.schemas.analysis import AnalysisRead
from app.schemas.report_payload import ReportPayload
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.llm.report_prompts import (
    build_report_structured_prompt_v9,
    format_facts_for_prompt,
)
from app.services.report.controlled_summary_workflow import (
    ControlledSummaryWorkflowDeps,
    render_controlled_summary_workflow,
)
from app.services.report.inline_structured_report_workflow import (
    InlineStructuredReportWorkflowDeps,
    InlineStructuredReportWorkflowInput,
    run_inline_structured_report_workflow,
)
from app.services.report.market_workflow import (
    build_controlled_markdown_result,
    build_market_enhancements,
    build_market_report_markdown,
)
from app.services.report.render_bundle import ControlledMarkdownResult
from app.services.report.report_assembly_workflow import (
    ReportAssemblyDeps,
    ReportAssemblyInput,
    assemble_report_payload,
)
from app.services.report.report_context_loader import (
    ReportContextLoaderDeps,
    load_report_request_context,
)
from app.services.report.report_enrichment_workflow import (
    ReportEnrichmentResult,
    write_report_enrichment_audit,
)
from app.services.report.report_request_workflow import ReportRequestWorkflowDeps
from app.services.report.structured_report_renderer import (
    render_structured_report_markdown,
)


@dataclass(slots=True)
class ReportAssemblyDepsFactoryInput:
    db: Any
    quality_level: str
    product_description: str
    market_report_enabled: bool
    prefer_market_report: bool
    enable_llm_summary: bool
    llm_model_name: str
    openai_api_key: str
    controlled_build_context: Callable[..., Any] | None
    controlled_render_report: Callable[..., Any] | None
    coerce_report_html: Callable[[str | None], str]
    fetch_member_count: Callable[[str], Any]
    client_factory: Callable[..., Any] = OpenAIChatClient
    format_facts: Callable[..., str] = format_facts_for_prompt
    build_prompt: Callable[..., str] = build_report_structured_prompt_v9


@dataclass(slots=True)
class ReportRequestDepsFactoryInput:
    load_task_with_analysis: Callable[[UUID], Awaitable[Any]]
    is_membership_allowed: Callable[[Any], bool]
    make_not_found_error: Callable[[str], Exception]
    make_access_denied_error: Callable[[str], Exception]
    make_not_ready_error: Callable[[str], Exception]
    cache_get: Callable[[str], Awaitable[ReportPayload | None]] | None
    cache_set: Callable[[str, ReportPayload], Awaitable[None]] | None
    validate_analysis_payload: Callable[[Any], AnalysisRead]
    assembly_deps: ReportAssemblyDeps
    prefer_market_report: bool


def build_report_assembly_deps(
    factory_input: ReportAssemblyDepsFactoryInput,
) -> ReportAssemblyDeps:
    async def _build_t1_market_report_md(
        analysis_payload: AnalysisRead | None = None,
    ) -> tuple[str | None, Any | None, list[Any] | None, bool]:
        return await build_market_report_markdown(
            factory_input.db,
            quality_level=factory_input.quality_level,
            product_description=factory_input.product_description,
            analysis_payload=analysis_payload,
        )

    async def _build_market_enhancements(
        analysis_payload: AnalysisRead,
    ) -> dict[str, Any] | None:
        return await build_market_enhancements(
            factory_input.db,
            analysis_payload,
            enabled=factory_input.market_report_enabled,
        )

    def _render_controlled_summary_markdown(
        *,
        analysis_payload: AnalysisRead,
        task_id: UUID,
        blocked_by_quality_gate: bool,
    ) -> tuple[str | None, dict[str, Any]]:
        result = render_controlled_summary_workflow(
            analysis_payload=analysis_payload,
            task_id=task_id,
            blocked_by_quality_gate=blocked_by_quality_gate,
            deps=ControlledSummaryWorkflowDeps(
                build_context=factory_input.controlled_build_context,
                render_report=factory_input.controlled_render_report,
            ),
        )
        return result.as_tuple()

    async def _build_controlled_report_markdown(
        analysis_payload: AnalysisRead,
        task_id: UUID,
        blocked_by_quality_gate: bool,
        inline_llm_enabled: bool,
    ) -> ControlledMarkdownResult:
        return await build_controlled_markdown_result(
            blocked_by_quality_gate=blocked_by_quality_gate,
            inline_llm_enabled=inline_llm_enabled,
            prefer_market_markdown=factory_input.prefer_market_report,
            build_market_markdown=lambda: _build_t1_market_report_md(analysis_payload),
            render_controlled_summary=lambda: _render_controlled_summary_markdown(
                analysis_payload=analysis_payload,
                task_id=task_id,
                blocked_by_quality_gate=blocked_by_quality_gate,
            ),
        )

    async def _build_inline_structured_report(
        task: Any,
        analysis_payload: AnalysisRead,
        blocked_by_quality_gate: bool,
        inline_llm_enabled: bool,
    ) -> dict[str, Any] | None:
        return await run_inline_structured_report_workflow(
            workflow_input=InlineStructuredReportWorkflowInput(
                task=task,
                analysis=analysis_payload,
                blocked_by_quality_gate=blocked_by_quality_gate,
                inline_llm_enabled=inline_llm_enabled,
            ),
            deps=InlineStructuredReportWorkflowDeps(
                enable_llm_summary=factory_input.enable_llm_summary,
                llm_model_name=factory_input.llm_model_name,
                openai_api_key=factory_input.openai_api_key,
                format_facts=factory_input.format_facts,
                build_prompt=factory_input.build_prompt,
                client_factory=lambda model, api_key: factory_input.client_factory(
                    model=model,
                    timeout=60.0,
                    api_key=api_key,
                ),
            ),
        )

    def _render_structured_markdown(task_obj: Any, analysis_payload: AnalysisRead) -> str:
        return render_structured_report_markdown(
            report_structured=analysis_payload.sources.report_structured,
            product_description=analysis_payload.sources.product_description
            or task_obj.product_description,
            facts_slice=analysis_payload.sources.facts_slice,
            pain_points=analysis_payload.insights.pain_points,
        )

    def _write_enrichment_audit(
        task_id: UUID,
        llm_model: str | None,
        enrichment_result: ReportEnrichmentResult,
    ) -> None:
        write_report_enrichment_audit(
            task_id=task_id,
            llm_model=llm_model,
            enrichment_result=enrichment_result,
        )

    return ReportAssemblyDeps(
        maybe_generate_structured_report=_build_inline_structured_report,
        build_market_enhancements=_build_market_enhancements,
        build_controlled_report_markdown=_build_controlled_report_markdown,
        render_structured_markdown=_render_structured_markdown,
        coerce_report_html=factory_input.coerce_report_html,
        fetch_member_count=factory_input.fetch_member_count,
        write_enrichment_audit=_write_enrichment_audit,
    )


def build_report_request_workflow_deps(
    factory_input: ReportRequestDepsFactoryInput,
) -> ReportRequestWorkflowDeps:
    async def _load_context(task_id: UUID, user_id: UUID) -> Any:
        return await load_report_request_context(
            task_id=task_id,
            user_id=user_id,
            deps=ReportContextLoaderDeps(
                load_task_with_analysis=factory_input.load_task_with_analysis,
                is_membership_allowed=factory_input.is_membership_allowed,
                make_not_found_error=factory_input.make_not_found_error,
                make_access_denied_error=factory_input.make_access_denied_error,
                make_not_ready_error=factory_input.make_not_ready_error,
            ),
        )

    async def _assemble_payload(
        task: Any,
        analysis_payload: AnalysisRead,
        inline_llm_enabled: bool,
    ) -> Any:
        return await assemble_report_payload(
            assembly_input=ReportAssemblyInput(
                task=task,
                analysis=analysis_payload,
                inline_llm_enabled=inline_llm_enabled,
                prefer_market_report=factory_input.prefer_market_report,
            ),
            deps=factory_input.assembly_deps,
        )

    return ReportRequestWorkflowDeps(
        load_context=_load_context,
        cache_get=factory_input.cache_get,
        cache_set=factory_input.cache_set,
        validate_analysis_payload=factory_input.validate_analysis_payload,
        assemble_payload=_assemble_payload,
    )


def default_membership_allowed(membership_level: Any) -> bool:
    return membership_level in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}


__all__ = [
    "ReportAssemblyDepsFactoryInput",
    "ReportRequestDepsFactoryInput",
    "build_report_assembly_deps",
    "build_report_request_workflow_deps",
    "default_membership_allowed",
]
