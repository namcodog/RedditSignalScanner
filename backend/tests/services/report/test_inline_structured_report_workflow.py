from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisRead, InsightsPayload, SourcesPayload
from app.services.report.inline_structured_report_workflow import (
    InlineStructuredReportWorkflowDeps,
    InlineStructuredReportWorkflowInput,
    run_inline_structured_report_workflow,
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
        confidence_score=Decimal("0.8"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
    )


class _FakeClient:
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.calls: list[tuple[str, int, float]] = []

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        self.calls.append((prompt, max_tokens, temperature))
        return self._raw


@pytest.mark.asyncio
async def test_inline_structured_report_workflow_short_circuits_when_disabled() -> None:
    analysis = _build_analysis()
    existing = {"market_health": {"ps_ratio": {"ratio": "1.0:1"}}}
    analysis.sources.report_structured = existing

    client = _FakeClient("{}")
    result = await run_inline_structured_report_workflow(
        workflow_input=InlineStructuredReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=InlineStructuredReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda model, api_key: client,
        ),
    )

    assert result == existing
    assert client.calls == []


@pytest.mark.asyncio
async def test_inline_structured_report_workflow_generates_payload_when_enabled() -> None:
    analysis = _build_analysis()
    client = _FakeClient(
        '{"market_health":{"ps_ratio":{"ratio":"1.2:1"}},"decision_cards":[]}'
    )

    result = await run_inline_structured_report_workflow(
        workflow_input=InlineStructuredReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=InlineStructuredReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda model, api_key: client,
        ),
    )

    assert result is not None
    assert result["market_health"]["ps_ratio"]["ratio"] == "1.2:1"
    assert len(client.calls) == 1
    assert client.calls[0][1] == 4000


@pytest.mark.asyncio
async def test_inline_structured_report_workflow_skips_when_model_or_key_invalid() -> None:
    analysis = _build_analysis()
    client = _FakeClient("{}")

    result = await run_inline_structured_report_workflow(
        workflow_input=InlineStructuredReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=InlineStructuredReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="local-extractive",
            openai_api_key="",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda model, api_key: client,
        ),
    )

    assert result is None
    assert client.calls == []


@pytest.mark.asyncio
async def test_inline_structured_report_workflow_returns_none_when_client_fails() -> None:
    analysis = _build_analysis()

    class _BrokenClient:
        async def generate(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
            raise RuntimeError("boom")

    result = await run_inline_structured_report_workflow(
        workflow_input=InlineStructuredReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=InlineStructuredReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda model, api_key: _BrokenClient(),
        ),
    )

    assert result is None
