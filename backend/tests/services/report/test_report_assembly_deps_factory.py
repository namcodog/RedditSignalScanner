from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisRead, InsightsPayload, SourcesPayload
from app.services.report.report_runtime import (
    ReportAssemblyDepsFactoryInput,
    build_report_assembly_deps,
)


def _build_analysis() -> AnalysisRead:
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
            cache_hit_rate=0.2,
            facts_slice={"trend_summary": {"summary": "讨论热度稳定"}},
        ),
        analysis_version="1.0",
        confidence_score=0.8,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_report_assembly_deps_factory_controlled_markdown_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.report.report_runtime_factory as mod

    captured: dict[str, object] = {}

    async def _fake_market_report_markdown(*args, **kwargs):
        captured["market_kwargs"] = kwargs
        return ("# market", None, None, False)

    def _fake_render_controlled_summary_workflow(*, analysis_payload, task_id, blocked_by_quality_gate, deps):
        captured["summary_task_id"] = task_id
        captured["summary_blocked"] = blocked_by_quality_gate
        return SimpleNamespace(as_tuple=lambda: ("# summary", {"source": "controlled"}))

    async def _fake_build_controlled_markdown_result(**kwargs):
        captured["controlled_kwargs"] = kwargs
        await kwargs["build_market_markdown"]()
        kwargs["render_controlled_summary"]()
        return SimpleNamespace(markdown="# controlled", metrics_data={}, llm_used=False, source="market")

    monkeypatch.setattr(mod, "build_market_report_markdown", _fake_market_report_markdown)
    monkeypatch.setattr(mod, "render_controlled_summary_workflow", _fake_render_controlled_summary_workflow)
    monkeypatch.setattr(mod, "build_controlled_markdown_result", _fake_build_controlled_markdown_result)

    deps = build_report_assembly_deps(
        ReportAssemblyDepsFactoryInput(
            db=object(),
            quality_level="standard",
            product_description="Demo",
            market_report_enabled=True,
            prefer_market_report=True,
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            controlled_build_context=Mock(),
            controlled_render_report=Mock(),
            coerce_report_html=lambda value: value or "",
            fetch_member_count=AsyncMock(return_value=0),
        )
    )

    analysis = _build_analysis()
    result = await deps.build_controlled_report_markdown(
        analysis,
        uuid4(),
        True,
        True,
    )

    assert result.markdown == "# controlled"
    assert captured["controlled_kwargs"]["prefer_market_markdown"] is True
    assert captured["summary_blocked"] is True
    assert captured["market_kwargs"]["analysis_payload"] is analysis


@pytest.mark.asyncio
async def test_report_assembly_deps_factory_inline_structured_report_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.report.report_runtime_factory as mod

    captured: dict[str, object] = {}

    async def _fake_inline_workflow(*, workflow_input, deps):
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return {"market_health": {"ps_ratio": {"ratio": "1.2:1"}}}

    monkeypatch.setattr(mod, "run_inline_structured_report_workflow", _fake_inline_workflow)

    deps = build_report_assembly_deps(
        ReportAssemblyDepsFactoryInput(
            db=object(),
            quality_level="standard",
            product_description="Demo",
            market_report_enabled=False,
            prefer_market_report=False,
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            controlled_build_context=None,
            controlled_render_report=None,
            coerce_report_html=lambda value: value or "",
            fetch_member_count=AsyncMock(return_value=0),
        )
    )

    task = SimpleNamespace(product_description="Task product")
    analysis = _build_analysis()
    result = await deps.maybe_generate_structured_report(task, analysis, False, True)

    assert result == {"market_health": {"ps_ratio": {"ratio": "1.2:1"}}}
    assert captured["workflow_input"].task is task
    assert captured["workflow_input"].analysis is analysis
    assert captured["workflow_input"].inline_llm_enabled is True
