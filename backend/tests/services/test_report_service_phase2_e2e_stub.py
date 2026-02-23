from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from app.core import config
from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.services.report_service import ReportService, ReportServiceConfig

# 避免自动重置数据库
os.environ.setdefault("SKIP_DB_RESET", "1")


@dataclass
class FakeReport:
    generated_at: datetime
    html_content: str


@dataclass
class FakeAnalysis:
    id: UUID
    task_id: UUID
    insights: dict[str, Any]
    sources: dict[str, Any]
    confidence_score: Decimal
    analysis_version: Any
    created_at: datetime
    report: FakeReport


@dataclass
class FakeUser:
    id: UUID
    membership_level: MembershipLevel = MembershipLevel.PRO


@dataclass
class FakeTask:
    id: UUID
    user_id: UUID
    status: TaskStatus
    analysis: Optional[FakeAnalysis]
    product_description: Optional[str] = None
    user: Optional[FakeUser] = None


class FakeRepository:
    def __init__(self, task: FakeTask) -> None:
        self._task = task

    async def get_task_with_analysis(self, task_id: UUID) -> FakeTask | None:
        if task_id == self._task.id:
            return self._task
        return None


def _fake_task() -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()
    insights = {
        "pain_points": [
            {"description": "费用不透明", "frequency": 8, "sentiment_score": -0.5, "severity": "high", "example_posts": []}
        ],
        "competitors": [{"name": "BrandA", "mentions": 5, "sentiment": "neutral", "layer": "summary"}],
        "opportunities": [{"description": "提升到账透明度", "relevance_score": 0.7, "potential_users": "10 teams"}],
        "action_items": [],
        "entity_summary": {"brands": [{"name": "BrandA", "mentions": 1}]},
    }
    sources = {"communities": ["r/homegym"], "posts_analyzed": 25, "cache_hit_rate": 0.82}
    analysis = FakeAnalysis(
        id=analysis_id,
        task_id=task_id,
        insights=insights,
        sources=sources,
        confidence_score=Decimal("0.71"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
        report=FakeReport(generated_at=datetime.now(timezone.utc), html_content="<html>demo</html>"),
    )
    return FakeTask(
        id=task_id,
        user_id=uuid4(),
        status=TaskStatus.COMPLETED,
        analysis=analysis,
        product_description="Demo",
        user=FakeUser(id=uuid4()),
    )


@pytest.mark.asyncio
async def test_phase2_stub_analyze_to_report(monkeypatch):
    # premium 模式 + 桩替换，验证 end-to-end 不依赖真实 DB
    monkeypatch.setattr(config.settings, "report_quality_level", "premium", raising=False)

    async def _stub_t1(self):  # type: ignore[override]
        return "# md", None, None, False

    async def _stub_llm(self, md: str):  # type: ignore[override]
        return md + "\nLLM", False

    monkeypatch.setattr(ReportService, "_build_t1_market_report_md", _stub_t1, raising=False)
    monkeypatch.setattr(ReportService, "_maybe_enhance_with_llm", _stub_llm, raising=False)

    task = _fake_task()
    repo = FakeRepository(task)
    service = ReportService(db=None, repository=repo, cache=None, config=ReportServiceConfig({}, 60, "1.0"))

    payload = await service.get_report(task.id, task.user_id)
    assert payload.report.pain_points
    assert payload.report.opportunities
    assert payload.metadata.confidence_score >= 0.7
    assert payload.metadata.analysis_version == "1.0"
    assert payload.data_source in {None, "real"}
