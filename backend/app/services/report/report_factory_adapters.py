from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Optional, Any
from uuid import UUID

from app.schemas.analysis import AnalysisRead
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
from app.services.report.narrative_report_workflow import (
    NarrativeReportWorkflowDeps,
    NarrativeReportWorkflowInput,
    run_narrative_report_workflow,
)
from app.services.report.report_assembly_workflow import (
    ReportAssemblyInput,
    assemble_report_payload,
)
from app.services.report.report_context_loader import (
    ReportContextLoaderDeps,
    load_report_request_context,
)


def make_market_report_builder(
    *,
    db: Any,
    quality_level: str,
    product_description: str,
    build_market_report_markdown_fn: Callable[...Optional[, Awaitable[tuple[str]Optional[, Any]Optional[, list[Any]], bool]]],
) ->Optional[ Callable[[AnalysisRead]Optional[], Awaitable[tuple[str]Optional[, Any]Optional[, list[Any]], bool]]]:
    async def _build_market_report_md(
        analysis_payload:Optional[ AnalysisRead] = None,
    ) ->Optional[ tuple[str]Optional[, Any]Optional[, list[Any]], bool]:
        return await build_market_report_markdown_fn(
            db,
            quality_level=quality_level,
            product_description=product_description,
            analysis_payload=analysis_payload,
        )

    return _build_market_report_md


def make_market_enhancements_builder(
    *,
    db: Any,
    enabled: bool,
    build_market_enhancements_fn: Callable[...Optional[, Awaitable[dict[str, Any]]]],
) ->Optional[ Callable[[AnalysisRead], Awaitable[dict[str, Any]]]]:
    async def _build_market_enhancements(
        analysis_payload: AnalysisRead,
    ) ->Optional[ dict[str, Any]]:
        return await build_market_enhancements_fn(
            db,
            analysis_payload,
            enabled=enabled,
        )

    return _build_market_enhancements


def make_controlled_summary_renderer(
    *,
    controlled_build_context: Callable[...Optional[, Any]],
    controlled_render_report: Callable[...Optional[, Any]],
    render_controlled_summary_workflow_fn: Callable[..., Any],
) -> Callable[...Optional[, tuple[str], dict[str, Any]]]:
    def _render_controlled_summary_markdown(
        *,
        analysis_payload: AnalysisRead,
        task_id: UUID,
        blocked_by_quality_gate: bool,
    ) ->Optional[ tuple[str], dict[str, Any]]:
        result = render_controlled_summary_workflow_fn(
            analysis_payload=analysis_payload,
            task_id=task_id,
            blocked_by_quality_gate=blocked_by_quality_gate,
            deps=ControlledSummaryWorkflowDeps(
                build_context=controlled_build_context,
                render_report=controlled_render_report,
            ),
        )
        return result.as_tuple()

    return _render_controlled_summary_markdown


def make_controlled_markdown_builder(
    *,
    prefer_market_report: bool,
    build_market_markdown:Optional[ Callable[[AnalysisRead]Optional[], Awaitable[tuple[str]Optional[, Any]Optional[, list[Any]], bool]]],
    render_controlled_summary: Callable[...Optional[, tuple[str], dict[str, Any]]],
    build_controlled_markdown_result_fn: Callable[..., Awaitable[Any]],
) -> Callable[[AnalysisRead, UUID, bool, bool], Awaitable[Any]]:
    async def _build_controlled_report_markdown(
        analysis_payload: AnalysisRead,
        task_id: UUID,
        blocked_by_quality_gate: bool,
        inline_llm_enabled: bool,
    ) -> Any:
        return await build_controlled_markdown_result_fn(
            blocked_by_quality_gate=blocked_by_quality_gate,
            inline_llm_enabled=inline_llm_enabled,
            prefer_market_markdown=prefer_market_report,
            build_market_markdown=lambda: build_market_markdown(analysis_payload),
            render_controlled_summary=lambda: render_controlled_summary(
                analysis_payload=analysis_payload,
                task_id=task_id,
                blocked_by_quality_gate=blocked_by_quality_gate,
            ),
        )

    return _build_controlled_report_markdown


def make_inline_structured_report_builder(
    *,
    enable_llm_summary: bool,
    llm_model_name: str,
    openai_api_key: str,
    format_facts: Callable[..., str],
    build_prompt: Callable[..., str],
    client_factory: Callable[..., Any],
    run_inline_structured_report_workflow_fn: Callable[...Optional[, Awaitable[dict[str, Any]]]],
) ->Optional[ Callable[[Any, AnalysisRead, bool, bool], Awaitable[dict[str, Any]]]]:
    async def _build_inline_structured_report(
        task: Any,
        analysis_payload: AnalysisRead,
        blocked_by_quality_gate: bool,
        inline_llm_enabled: bool,
    ) ->Optional[ dict[str, Any]]:
        return await run_inline_structured_report_workflow_fn(
            workflow_input=InlineStructuredReportWorkflowInput(
                task=task,
                analysis=analysis_payload,
                blocked_by_quality_gate=blocked_by_quality_gate,
                inline_llm_enabled=inline_llm_enabled,
            ),
            deps=InlineStructuredReportWorkflowDeps(
                enable_llm_summary=enable_llm_summary,
                llm_model_name=llm_model_name,
                openai_api_key=openai_api_key,
                format_facts=format_facts,
                build_prompt=build_prompt,
                client_factory=lambda model, api_key: client_factory(
                    model=model,
                    timeout=60.0,
                    api_key=api_key,
                ),
            ),
        )

    return _build_inline_structured_report


def make_narrative_report_builder(
    *,
    enable_llm_summary: bool,
    llm_model_name: str,
    openai_api_key: str,
    format_facts: Callable[..., str],
    build_prompt: Callable[..., str | list[dict[str, str]]],
    client_factory: Callable[..., Any],
    run_narrative_report_workflow_fn: Callable[...Optional[, Awaitable[tuple[str], bool]]],
) ->Optional[ Callable[[Any, AnalysisRead, bool, bool], Awaitable[tuple[str], bool]]]:
    async def _build_narrative_report_markdown(
        task: Any,
        analysis_payload: AnalysisRead,
        blocked_by_quality_gate: bool,
        inline_llm_enabled: bool,
    ) ->Optional[ tuple[str], bool]:
        return await run_narrative_report_workflow_fn(
            workflow_input=NarrativeReportWorkflowInput(
                task=task,
                analysis=analysis_payload,
                blocked_by_quality_gate=blocked_by_quality_gate,
                inline_llm_enabled=inline_llm_enabled,
            ),
            deps=NarrativeReportWorkflowDeps(
                enable_llm_summary=enable_llm_summary,
                llm_model_name=llm_model_name,
                openai_api_key=openai_api_key,
                format_facts=format_facts,
                build_prompt=build_prompt,
                client_factory=lambda model, api_key: client_factory(
                    model=model,
                    timeout=60.0,
                    api_key=api_key,
                ),
            ),
        )

    return _build_narrative_report_markdown


def make_request_context_loader(
    *,
    load_task_with_analysis: Callable[[UUID], Awaitable[Any]],
    is_membership_allowed: Callable[[Any], bool],
    make_not_found_error: Callable[[str], Exception],
    make_access_denied_error: Callable[[str], Exception],
    make_not_ready_error: Callable[[str], Exception],
    load_report_request_context_fn: Callable[..., Awaitable[Any]],
) -> Callable[[UUID, UUID], Awaitable[Any]]:
    async def _load_context(task_id: UUID, user_id: UUID) -> Any:
        return await load_report_request_context_fn(
            task_id=task_id,
            user_id=user_id,
            deps=ReportContextLoaderDeps(
                load_task_with_analysis=load_task_with_analysis,
                is_membership_allowed=is_membership_allowed,
                make_not_found_error=make_not_found_error,
                make_access_denied_error=make_access_denied_error,
                make_not_ready_error=make_not_ready_error,
            ),
        )

    return _load_context


def make_report_payload_assembler(
    *,
    assembly_deps: Any,
    prefer_market_report: bool,
    assemble_report_payload_fn: Callable[..., Awaitable[Any]],
) -> Callable[[Any, AnalysisRead, bool], Awaitable[Any]]:
    async def _assemble_payload(
        task: Any,
        analysis_payload: AnalysisRead,
        inline_llm_enabled: bool,
    ) -> Any:
        return await assemble_report_payload_fn(
            assembly_input=ReportAssemblyInput(
                task=task,
                analysis=analysis_payload,
                inline_llm_enabled=inline_llm_enabled,
                prefer_market_report=prefer_market_report,
            ),
            deps=assembly_deps,
        )

    return _assemble_payload


__all__ = [
    "make_controlled_markdown_builder",
    "make_controlled_summary_renderer",
    "make_inline_structured_report_builder",
    "make_market_enhancements_builder",
    "make_market_report_builder",
    "make_narrative_report_builder",
    "make_report_payload_assembler",
    "make_request_context_loader",
]
