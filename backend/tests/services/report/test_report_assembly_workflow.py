from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisRead, InsightsPayload, SourcesPayload
from app.services.report.render_bundle import ControlledMarkdownResult
from app.services.report.report_assembly_workflow import (
    ReportAssemblyDeps,
    ReportAssemblyInput,
    assemble_report_payload,
)
from app.services.report.report_enrichment_workflow import ReportEnrichmentResult


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
async def test_report_assembly_workflow_generates_structured_report_and_audits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.report.report_assembly_workflow as workflow_module

    task = _build_task()
    analysis = _build_analysis()
    captured: dict[str, object] = {}
    audit_calls: list[tuple[object, object]] = []

    async def _fake_enrichment_result(*, enrichment_input):  # type: ignore[no-untyped-def]
        captured["blocked"] = enrichment_input.blocked_by_quality_gate
        return ReportEnrichmentResult(
            action_items=[],
            normalization_rate=0.0,
            normalization_details=[],
        )

    def _fake_render_bundle(**kwargs):  # type: ignore[no-untyped-def]
        captured["render_bundle"] = kwargs
        return SimpleNamespace(
            report_html=kwargs["base_report_html"],
            market_enhancements=kwargs["market_enhancements"],
            llm_used=False,
            metrics_summary={},
        )

    async def _fake_build_payload(*, build_input, fetch_member_count):  # type: ignore[no-untyped-def]
        captured["report_structured"] = build_input.analysis.sources.report_structured
        return SimpleNamespace(metadata=SimpleNamespace(llm_model="gpt-4o-mini"))

    monkeypatch.setattr(
        workflow_module,
        "build_report_enrichment_result",
        _fake_enrichment_result,
    )
    monkeypatch.setattr(
        workflow_module,
        "build_report_render_bundle",
        _fake_render_bundle,
    )
    monkeypatch.setattr(
        workflow_module,
        "build_report_payload",
        _fake_build_payload,
    )

    async def _maybe_generate(*_args):  # type: ignore[no-untyped-def]
        return {
            "market_health": {
                "ps_ratio": {
                    "ratio": "1.2:1",
                }
            }
        }

    async def _build_market_enhancements(*_args):  # type: ignore[no-untyped-def]
        return {"mode": "community_market"}

    async def _build_controlled_report_markdown(*_args):  # type: ignore[no-untyped-def]
        raise AssertionError("controlled markdown should not run when html already exists")

    async def _fetch_member_count(_community: str) -> int:
        return 0

    result = await assemble_report_payload(
        assembly_input=ReportAssemblyInput(
            task=task,
            analysis=analysis,
            inline_llm_enabled=True,
        ),
        deps=ReportAssemblyDeps(
            maybe_generate_structured_report=_maybe_generate,
            build_market_enhancements=_build_market_enhancements,
            build_controlled_report_markdown=_build_controlled_report_markdown,
            render_structured_markdown=lambda *_args: "## structured",
            coerce_report_html=lambda raw: f"<p>{raw}</p>" if raw else "",
            fetch_member_count=_fetch_member_count,
            write_enrichment_audit=lambda task_id, llm_model, enrichment_result: audit_calls.append(
                (task_id, llm_model)
            ),
        ),
    )

    assert result.blocked_by_quality_gate is False
    assert captured["blocked"] is False
    assert isinstance(captured["report_structured"], dict)
    assert analysis.sources.report_structured is not None
    assert audit_calls == [(task.id, "gpt-4o-mini")]
    assert result.payload.metadata.llm_model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_report_assembly_workflow_falls_back_to_controlled_when_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.report.report_assembly_workflow as workflow_module

    task = _build_task(html_content="")
    analysis = _build_analysis(report_tier="X_blocked")
    captured: dict[str, object] = {}

    async def _fake_enrichment_result(*, enrichment_input):  # type: ignore[no-untyped-def]
        captured["blocked"] = enrichment_input.blocked_by_quality_gate
        return ReportEnrichmentResult(
            action_items=[],
            normalization_rate=0.0,
            normalization_details=[],
        )

    def _fake_render_bundle(**kwargs):  # type: ignore[no-untyped-def]
        captured["render_bundle"] = kwargs
        return SimpleNamespace(
            report_html="<html>controlled</html>",
            market_enhancements=kwargs["market_enhancements"],
            llm_used=False,
            metrics_summary={"source": "controlled"},
        )

    async def _fake_build_payload(*, build_input, fetch_member_count):  # type: ignore[no-untyped-def]
        captured["payload_report_structured"] = build_input.analysis.sources.report_structured
        return SimpleNamespace(metadata=SimpleNamespace(llm_model=None))

    monkeypatch.setattr(
        workflow_module,
        "build_report_enrichment_result",
        _fake_enrichment_result,
    )
    monkeypatch.setattr(
        workflow_module,
        "build_report_render_bundle",
        _fake_render_bundle,
    )
    monkeypatch.setattr(
        workflow_module,
        "build_report_payload",
        _fake_build_payload,
    )

    blocked_flags: list[tuple[bool, bool]] = []
    controlled_calls: list[tuple[bool, bool]] = []

    async def _maybe_generate(_task, _analysis, blocked_by_quality_gate, inline_llm_enabled):  # type: ignore[no-untyped-def]
        blocked_flags.append((blocked_by_quality_gate, inline_llm_enabled))
        return None

    async def _build_market_enhancements(*_args):  # type: ignore[no-untyped-def]
        return None

    async def _build_controlled_report_markdown(_analysis, _task_id, blocked_by_quality_gate, inline_llm_enabled):  # type: ignore[no-untyped-def]
        controlled_calls.append((blocked_by_quality_gate, inline_llm_enabled))
        return ControlledMarkdownResult(
            markdown="## controlled",
            metrics_data={"quality": "fallback"},
            llm_used=False,
            source="executive_summary",
        )

    async def _fetch_member_count(_community: str) -> int:
        return 0

    result = await assemble_report_payload(
        assembly_input=ReportAssemblyInput(
            task=task,
            analysis=analysis,
            inline_llm_enabled=True,
        ),
        deps=ReportAssemblyDeps(
            maybe_generate_structured_report=_maybe_generate,
            build_market_enhancements=_build_market_enhancements,
            build_controlled_report_markdown=_build_controlled_report_markdown,
            render_structured_markdown=lambda *_args: None,
            coerce_report_html=lambda _raw: "",
            fetch_member_count=_fetch_member_count,
            write_enrichment_audit=lambda *_args: None,
        ),
    )

    assert result.blocked_by_quality_gate is True
    assert captured["blocked"] is True
    assert blocked_flags == [(True, True)]
    assert controlled_calls == [(True, True)]
    render_bundle = captured["render_bundle"]
    assert isinstance(render_bundle, dict)
    assert render_bundle["base_report_html"] is None
    assert result.payload.metadata.llm_model is None
