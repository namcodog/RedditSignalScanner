from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.schemas.analysis import AnalysisRead
from app.schemas.report_payload import ReportPayload
from app.services.report.render_bundle import (
    ControlledMarkdownResult,
    build_report_render_bundle,
)
from app.services.report.report_enrichment_workflow import (
    ReportEnrichmentInput,
    ReportEnrichmentResult,
    build_report_enrichment_result,
)
from app.services.report.report_payload_builder import (
    ReportPayloadBuildInput,
    build_report_payload,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportAssemblyInput:
    task: Any
    analysis: AnalysisRead
    inline_llm_enabled: bool
    prefer_market_report: bool = False


@dataclass(slots=True)
class ReportAssemblyDeps:
    maybe_generate_structured_report: Callable[
        [Any, AnalysisRead, bool, bool],
        Awaitable[dict[str, Any] | None],
    ]
    build_market_enhancements: Callable[
        [AnalysisRead],
        Awaitable[dict[str, Any] | None],
    ]
    build_controlled_report_markdown: Callable[
        [AnalysisRead, UUID, bool, bool],
        Awaitable[ControlledMarkdownResult],
    ]
    render_structured_markdown: Callable[[Any, AnalysisRead], str | None]
    coerce_report_html: Callable[[str | None], str]
    fetch_member_count: Callable[[str], Awaitable[int]]
    write_enrichment_audit: Callable[[UUID, str | None, ReportEnrichmentResult], None]


@dataclass(slots=True)
class ReportAssemblyResult:
    payload: ReportPayload
    enrichment_result: ReportEnrichmentResult
    blocked_by_quality_gate: bool


def _is_blocked_by_quality_gate(analysis: AnalysisRead) -> bool:
    report_tier = str(analysis.sources.report_tier or "").strip()
    analysis_blocked = str(analysis.sources.analysis_blocked or "").strip()
    return report_tier in {"X_blocked", "C_scouting"} or analysis_blocked in {
        "quality_gate_blocked",
        "scouting_brief",
    }


def _empty_controlled_result() -> ControlledMarkdownResult:
    return ControlledMarkdownResult(
        markdown=None,
        metrics_data={},
        llm_used=False,
        source=None,
    )


async def assemble_report_payload(
    *,
    assembly_input: ReportAssemblyInput,
    deps: ReportAssemblyDeps,
) -> ReportAssemblyResult:
    blocked_by_quality_gate = _is_blocked_by_quality_gate(assembly_input.analysis)

    structured_report = await deps.maybe_generate_structured_report(
        assembly_input.task,
        assembly_input.analysis,
        blocked_by_quality_gate,
        assembly_input.inline_llm_enabled,
    )
    if structured_report:
        assembly_input.analysis.sources.report_structured = structured_report

    enrichment_result = await build_report_enrichment_result(
        enrichment_input=ReportEnrichmentInput(
            analysis=assembly_input.analysis,
            blocked_by_quality_gate=blocked_by_quality_gate,
            inline_llm_enabled=assembly_input.inline_llm_enabled,
        )
    )

    structured_markdown = deps.render_structured_markdown(
        assembly_input.task,
        assembly_input.analysis,
    )
    task_report = getattr(getattr(assembly_input.task, "analysis", None), "report", None)
    report_html_content = deps.coerce_report_html(
        structured_markdown or getattr(task_report, "html_content", "")
    )
    use_controlled_html = assembly_input.prefer_market_report or not bool(
        report_html_content
    )

    market_enhancements: dict[str, Any] | None = None
    try:
        market_enhancements = await deps.build_market_enhancements(
            assembly_input.analysis
        )
    except Exception as exc:
        logger.warning("failed to build market enhancements: %s", exc)

    controlled_result = _empty_controlled_result()
    if use_controlled_html:
        controlled_result = await deps.build_controlled_report_markdown(
            assembly_input.analysis,
            assembly_input.task.id,
            blocked_by_quality_gate,
            assembly_input.inline_llm_enabled,
        )

    render_bundle = build_report_render_bundle(
        base_report_html=report_html_content or None,
        controlled_result=controlled_result,
        blocked_by_quality_gate=blocked_by_quality_gate,
        market_enhancements=market_enhancements,
    )

    payload = await build_report_payload(
        build_input=ReportPayloadBuildInput(
            task=assembly_input.task,
            analysis=assembly_input.analysis,
            generated_at=task_report.generated_at,
            action_items=enrichment_result.action_items,
            render_bundle=render_bundle,
        ),
        fetch_member_count=deps.fetch_member_count,
    )

    try:
        deps.write_enrichment_audit(
            assembly_input.task.id,
            payload.metadata.llm_model,
            enrichment_result,
        )
    except Exception:
        pass

    return ReportAssemblyResult(
        payload=payload,
        enrichment_result=enrichment_result,
        blocked_by_quality_gate=blocked_by_quality_gate,
    )
