from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Any, Awaitable, Callable
from uuid import UUID

from app.schemas.analysis import AnalysisRead
from app.services.report.render_bundle import (
    ControlledMarkdownResult,
    ReportRenderBundle,
    build_report_render_bundle,
)
from app.services.report.structured_report_fallback import (
    enforce_structured_report_contract,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CanonicalAssemblyInput:
    task: Any
    analysis: AnalysisRead
    blocked_by_quality_gate: bool
    inline_llm_enabled: bool
    prefer_market_report: bool = False


@dataclass(slots=True)
class CanonicalAssemblyDeps:
    maybe_generate_structured_report: Callable[
        [Any, AnalysisRead, bool, bool],
Optional[        Awaitable[dict[str, Any]]],
    ]
    build_narrative_report_markdown: Callable[
        [Any, AnalysisRead, bool, bool],
Optional[        Awaitable[tuple[str], bool]],
    ]
    build_market_enhancements: Callable[
        [AnalysisRead],
Optional[        Awaitable[dict[str, Any]]],
    ]
    build_controlled_report_markdown: Callable[
        [AnalysisRead, UUID, bool, bool],
        Awaitable[ControlledMarkdownResult],
    ]
    render_structured_markdown:Optional[ Callable[[Any, AnalysisRead], str]]
    coerce_report_html:Optional[ Callable[[str]], str]


@dataclass(slots=True)
class CanonicalAssemblyResult:
    render_bundle: ReportRenderBundle
    task_report: Any


def empty_controlled_result() -> ControlledMarkdownResult:
    return ControlledMarkdownResult(
        markdown=None,
        metrics_data={},
        llm_used=False,
        source=None,
    )


async def assemble_canonical_report(
    *,
    assembly_input: CanonicalAssemblyInput,
    deps: CanonicalAssemblyDeps,
) -> CanonicalAssemblyResult:
    structured_report = await deps.maybe_generate_structured_report(
        assembly_input.task,
        assembly_input.analysis,
        assembly_input.blocked_by_quality_gate,
        assembly_input.inline_llm_enabled,
    )
    assembly_input.analysis.sources.report_structured = enforce_structured_report_contract(
        task=assembly_input.task,
        insights=assembly_input.analysis.insights.model_dump(mode="json"),
        sources=assembly_input.analysis.sources.model_dump(mode="json"),
        report_tier=str(assembly_input.analysis.sources.report_tier or "").strip()
        or "A_full",
        candidate=structured_report or assembly_input.analysis.sources.report_structured,
    )

    structured_markdown = deps.render_structured_markdown(
        assembly_input.task,
        assembly_input.analysis,
    )
    narrative_markdown, narrative_llm_used = await deps.build_narrative_report_markdown(
        assembly_input.task,
        assembly_input.analysis,
        assembly_input.blocked_by_quality_gate,
        assembly_input.inline_llm_enabled,
    )
    report_markdown = narrative_markdown or structured_markdown
    task_report = getattr(getattr(assembly_input.task, "analysis", None), "report", None)
    report_html_content = deps.coerce_report_html(
        report_markdown or getattr(task_report, "html_content", "")
    )
    use_controlled_html = assembly_input.prefer_market_report or not bool(
        report_html_content
    )

    market_enhancements:Optional[ dict[str, Any]] = None
    try:
        market_enhancements = await deps.build_market_enhancements(
            assembly_input.analysis
        )
    except Exception as exc:
        logger.warning("failed to build market enhancements: %s", exc)

    controlled_result = empty_controlled_result()
    if use_controlled_html:
        controlled_result = await deps.build_controlled_report_markdown(
            assembly_input.analysis,
            assembly_input.task.id,
            assembly_input.blocked_by_quality_gate,
            assembly_input.inline_llm_enabled,
        )

    render_bundle = build_report_render_bundle(
        base_report_markdown=report_markdown,
        base_report_html=report_html_content or None,
        controlled_result=controlled_result,
        blocked_by_quality_gate=assembly_input.blocked_by_quality_gate,
        market_enhancements=market_enhancements,
        narrative_llm_used=narrative_llm_used,
    )
    return CanonicalAssemblyResult(
        render_bundle=render_bundle,
        task_report=task_report,
    )


__all__ = [
    "CanonicalAssemblyDeps",
    "CanonicalAssemblyInput",
    "CanonicalAssemblyResult",
    "assemble_canonical_report",
    "empty_controlled_result",
]
