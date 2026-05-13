from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisRead, InsightsPayload, SourcesPayload
from app.services.report.render_bundle import ControlledMarkdownResult
from app.services.report.report_canonical_assembly import (
    CanonicalAssemblyDeps,
    CanonicalAssemblyInput,
    assemble_canonical_report,
)


def _build_analysis(*, report_tier: str | None = None) -> AnalysisRead:
    return AnalysisRead(
        id=uuid4(),
        task_id=uuid4(),
        insights=InsightsPayload(
            pain_points=[],
            competitors=[],
            opportunities=[],
            action_items=[],
        ),
        sources=SourcesPayload(
            communities=["r/demo"],
            posts_analyzed=12,
            cache_hit_rate=0.4,
            report_tier=report_tier,
        ),
        confidence_score=Decimal("0.8"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
    )


def _build_task(html_content: str = "<html>seed</html>") -> SimpleNamespace:
    report = SimpleNamespace(
        generated_at=datetime.now(timezone.utc),
        html_content=html_content,
    )
    analysis = SimpleNamespace(report=report)
    return SimpleNamespace(
        id=uuid4(),
        product_description="Demo",
        analysis=analysis,
    )


@pytest.mark.asyncio
async def test_assemble_canonical_report_prefers_narrative_html_when_available() -> None:
    task = _build_task()
    analysis = _build_analysis()

    async def _maybe_generate(*_args):  # type: ignore[no-untyped-def]
        return {"decision_cards": [{"title": "需求趋势", "conclusion": "需求在涨。"}]}

    async def _build_narrative(*_args):  # type: ignore[no-untyped-def]
        return ("# narrative", True)

    async def _build_market_enhancements(*_args):  # type: ignore[no-untyped-def]
        return {"mode": "community_market"}

    async def _build_controlled(*_args):  # type: ignore[no-untyped-def]
        raise AssertionError("controlled markdown should not run when html already exists")

    result = await assemble_canonical_report(
        assembly_input=CanonicalAssemblyInput(
            task=task,
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=CanonicalAssemblyDeps(
            maybe_generate_structured_report=_maybe_generate,
            build_narrative_report_markdown=_build_narrative,
            build_market_enhancements=_build_market_enhancements,
            build_controlled_report_markdown=_build_controlled,
            render_structured_markdown=lambda *_args: "## structured",
            coerce_report_html=lambda raw: f"<p>{raw}</p>" if raw else "",
        ),
    )

    assert analysis.sources.report_structured is not None
    assert result.render_bundle.report_html == "<p># narrative</p>"
    assert result.render_bundle.market_enhancements == {"mode": "community_market"}


@pytest.mark.asyncio
async def test_assemble_canonical_report_falls_back_to_controlled_when_html_missing() -> None:
    task = _build_task(html_content="")
    analysis = _build_analysis(report_tier="X_blocked")
    controlled_calls: list[tuple[bool, bool]] = []

    async def _maybe_generate(*_args):  # type: ignore[no-untyped-def]
        return None

    async def _build_narrative(*_args):  # type: ignore[no-untyped-def]
        return (None, False)

    async def _build_market_enhancements(*_args):  # type: ignore[no-untyped-def]
        return None

    async def _build_controlled(_analysis, _task_id, blocked_by_quality_gate, inline_llm_enabled):  # type: ignore[no-untyped-def]
        controlled_calls.append((blocked_by_quality_gate, inline_llm_enabled))
        return ControlledMarkdownResult(
            markdown="## controlled",
            metrics_data={"quality": "fallback"},
            llm_used=False,
            source="executive_summary",
        )

    result = await assemble_canonical_report(
        assembly_input=CanonicalAssemblyInput(
            task=task,
            analysis=analysis,
            blocked_by_quality_gate=True,
            inline_llm_enabled=True,
        ),
        deps=CanonicalAssemblyDeps(
            maybe_generate_structured_report=_maybe_generate,
            build_narrative_report_markdown=_build_narrative,
            build_market_enhancements=_build_market_enhancements,
            build_controlled_report_markdown=_build_controlled,
            render_structured_markdown=lambda *_args: None,
            coerce_report_html=lambda _raw: "",
        ),
    )

    assert controlled_calls == [(True, True)]
    assert result.render_bundle.report_markdown == "## controlled"
    assert result.render_bundle.metrics_summary is not None
