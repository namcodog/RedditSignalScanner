from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis.analysis_rendering import (
    StructuredReportRenderResult,
    render_analysis_reports,
)


@pytest.mark.asyncio
async def test_render_analysis_reports_returns_blocked_bundle_for_x_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _stub_structured(**_: object) -> StructuredReportRenderResult:
        return StructuredReportRenderResult(
            report=None,
            status="skipped",
            reason="tier_skipped",
            model=None,
            rounds=0,
        )

    monkeypatch.setattr(
        "app.services.analysis.analysis_rendering.render_structured_report_with_llm",
        _stub_structured,
    )

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Test product",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    bundle = await render_analysis_reports(
        task=task,
        communities=[],
        insights={"pain_points": [], "competitors": [], "opportunities": [], "action_items": []},
        sources={"keywords": ["test"]},
        facts_slice={"market_health": {}},
        report_tier="X_blocked",
        settings=SimpleNamespace(
            enable_llm_summary=True,
            llm_model_name="gpt-4o-mini",
            openai_api_key="test-key",
        ),
        blocked_flags=["topic_mismatch"],
        blocked_suggestion="先扩充样本",
    )

    assert "报告拦截" in bundle.report_html
    assert "topic_mismatch" in bundle.report_html
    assert bundle.structured_render.status == "completed"
    assert bundle.structured_render.reason == "deterministic_fallback"
    assert isinstance(bundle.structured_render.report, dict)
    structured = bundle.structured_render.report
    assert "decision_cards" in structured
    assert "market_health" in structured
    assert "battlefields" in structured
    assert "pain_points" in structured
    assert "drivers" in structured
    assert "opportunities" in structured
