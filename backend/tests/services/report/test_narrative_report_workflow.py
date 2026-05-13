from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisRead, InsightsPayload, SourcesPayload
from app.services.report.narrative_report_workflow import (
    NarrativeReportWorkflowDeps,
    NarrativeReportWorkflowInput,
    run_narrative_report_workflow,
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
            report_structured={
                "decision_cards": [{"title": "需求趋势", "conclusion": "热度稳定", "details": ["样本稳定"]}],
                "market_health": {
                    "competition_saturation": {
                        "level": "中等",
                        "details": ["已有讨论"],
                        "interpretation": "仍有空间",
                    },
                    "ps_ratio": {
                        "ratio": "1.2:1",
                        "conclusion": "问题略多",
                        "interpretation": "可继续深挖",
                        "health_assessment": "可做",
                    },
                },
                "battlefields": [],
                "pain_points": [],
                "drivers": [],
                "opportunities": [],
            },
            facts_slice={"trend_summary": {"summary": "讨论热度稳定"}},
        ),
        confidence_score=Decimal("0.8"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
    )


class _FakeClient:
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.calls: list[tuple[object, int, float]] = []

    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        self.calls.append((prompt, max_tokens, temperature))
        return self._raw


@pytest.mark.asyncio
async def test_narrative_report_workflow_generates_markdown_when_enabled() -> None:
    analysis = _build_analysis()
    client = _FakeClient(
        """```markdown
# Demo report

## 1. 开篇概览
内容

## 2. 决策风向标
需求趋势

## 3. 概览（市场健康度诊断）
内容

## 4. 核心战场推荐（画像分级）
内容

## 5. 用户痛点拆解
内容

## 6. 关键决策驱动力
内容

## 7. 商业机会
内容
```"""
    )

    markdown, llm_used = await run_narrative_report_workflow(
        workflow_input=NarrativeReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=NarrativeReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: [
                {"role": "system", "content": product_description},
                {"role": "user", "content": facts_text},
            ],
            client_factory=lambda _model, _api_key: client,
        ),
    )

    assert llm_used is True
    assert markdown is not None
    assert markdown.startswith("# Demo report")
    assert "## 7. 商业机会" in markdown
    assert len(client.calls) == 1
    assert client.calls[0][1] == 7000
    assert "【report_brief】" in str(client.calls[0][0])


@pytest.mark.asyncio
async def test_narrative_report_workflow_does_not_require_inline_report_flag() -> None:
    analysis = _build_analysis()
    client = _FakeClient(
        """# Narrative from canonical

## 1. 开篇概览
内容

## 2. 决策风向标
需求趋势

## 3. 概览（市场健康度诊断）
内容

## 4. 核心战场推荐（画像分级）
内容

## 5. 用户痛点拆解
内容

## 6. 关键决策驱动力
内容

## 7. 商业机会
内容"""
    )

    markdown, llm_used = await run_narrative_report_workflow(
        workflow_input=NarrativeReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=False,
        ),
        deps=NarrativeReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda _model, _api_key: client,
        ),
    )

    assert markdown == client._raw
    assert llm_used is True
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_narrative_report_workflow_skips_when_model_or_key_invalid() -> None:
    analysis = _build_analysis()
    client = _FakeClient("# ignored")

    markdown, llm_used = await run_narrative_report_workflow(
        workflow_input=NarrativeReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=False,
            inline_llm_enabled=True,
        ),
        deps=NarrativeReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="local-extractive",
            openai_api_key="",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda _model, _api_key: client,
        ),
    )

    assert markdown is None
    assert llm_used is False
    assert client.calls == []


@pytest.mark.asyncio
async def test_narrative_report_workflow_skips_when_blocked_or_missing_structured() -> None:
    analysis = _build_analysis()
    analysis.sources.report_structured = None
    client = _FakeClient("# ignored")

    markdown, llm_used = await run_narrative_report_workflow(
        workflow_input=NarrativeReportWorkflowInput(
            task=SimpleNamespace(product_description="Demo product"),
            analysis=analysis,
            blocked_by_quality_gate=True,
            inline_llm_enabled=True,
        ),
        deps=NarrativeReportWorkflowDeps(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
            format_facts=lambda facts_slice: str(facts_slice),
            build_prompt=lambda product_description, facts_text: f"{product_description}\n{facts_text}",
            client_factory=lambda _model, _api_key: client,
        ),
    )

    assert markdown is None
    assert llm_used is False
    assert client.calls == []
