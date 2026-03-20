from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.analysis import (
    AnalysisRead,
    EvidenceItemOut,
    InsightsPayload,
    OpportunityReportOut,
    SourcesPayload,
)
from app.services.report.report_enrichment_workflow import (
    ReportEnrichmentInput,
    ReportEnrichmentResult,
    build_report_enrichment_result,
    write_report_enrichment_audit,
)


def _build_analysis_with_action_item() -> AnalysisRead:
    return AnalysisRead(
        id=uuid4(),
        task_id=uuid4(),
        insights=InsightsPayload(
            pain_points=[],
            competitors=[],
            opportunities=[],
            action_items=[
                OpportunityReportOut(
                    problem_definition="回款慢导致现金流紧张，团队很难周转。",
                    evidence_chain=[
                        EvidenceItemOut(
                            title="用户反馈",
                            url="https://example.com/post-1",
                            note="回款太慢",
                        )
                    ],
                    suggested_actions=[],
                    confidence=0.6,
                    urgency=0.7,
                    product_fit=0.5,
                    priority=0.65,
                )
            ],
        ),
        sources=SourcesPayload(
            communities=["r/demo"],
            posts_analyzed=12,
            cache_hit_rate=0.2,
        ),
        confidence_score=Decimal("0.8"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_build_report_enrichment_result_marks_sparse_evidence_and_defaults() -> None:
    analysis = _build_analysis_with_action_item()

    result = await build_report_enrichment_result(
        enrichment_input=ReportEnrichmentInput(
            analysis=analysis,
            blocked_by_quality_gate=True,
            inline_llm_enabled=False,
        )
    )

    assert result.normalization_rate == 0.0
    assert result.normalization_details == []
    assert len(result.action_items) == 1
    action_item = result.action_items[0]
    assert action_item.category == "strategy"
    assert action_item.title == "回款慢导致现金流紧张，团队很难周转"
    assert "证据不足(n<2)" in action_item.suggested_actions


def test_write_report_enrichment_audit_persists_details(tmp_path) -> None:
    task_id = uuid4()
    result = ReportEnrichmentResult(
        action_items=[],
        normalization_rate=0.42,
        normalization_details=[
            {
                "original": "Amazon seller central",
                "mapped": "Amazon",
                "confidence": 0.91,
                "accepted": True,
                "via": "openai",
                "candidates": 12,
            }
        ],
    )

    write_report_enrichment_audit(
        task_id=task_id,
        llm_model="gpt-4o-mini",
        enrichment_result=result,
        output_root=tmp_path,
    )

    payload = json.loads((tmp_path / f"llm-audit-{task_id}.json").read_text(encoding="utf-8"))
    assert payload["task_id"] == str(task_id)
    assert payload["llm_model"] == "gpt-4o-mini"
    assert payload["normalization_rate"] == 0.42
    assert payload["details"]["normalizations"][0]["mapped"] == "Amazon"
