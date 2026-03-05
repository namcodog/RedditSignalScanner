from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.services.report.report_service import ReportService, ReportServiceConfig


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


def _fake_task_basic() -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()

    insights = {
        "pain_points": [
            {
                "description": "订阅费太贵",
                "frequency": 5,
                "sentiment_score": -0.6,
                "severity": "high",
                "example_posts": [],
                "user_examples": [],
            }
        ],
        "competitors": [
            {"name": "GenericBrand", "mentions": 10, "sentiment": "neutral", "layer": "summary"}
        ],
        "opportunities": [],
        "action_items": [
            {
                "problem_definition": "订阅费陷阱",
                "evidence_chain": [
                    {"title": "case A", "url": "https://reddit.com/a", "note": "示例"}
                ],
                "suggested_actions": ["Add retry"],
                "confidence": 0.8,
                "urgency": 0.7,
                "product_fit": 0.8,
                "priority": 0.6,
            }
        ],
        "entity_summary": {"brands": [{"name": "GenericBrand", "mentions": 1}]},
    }

    sources = {
        "communities": ["r/homegym"],
        "posts_analyzed": 15,
        "cache_hit_rate": 0.8,
        "communities_detail": [
            {
                "name": "r/homegym",
                "categories": ["fitness"],
                "mentions": 20,
                "daily_posts": 100,
                "avg_comment_length": 60,
                "cache_hit_rate": 0.9,
                "from_cache": True,
            }
        ],
    }

    analysis = FakeAnalysis(
        id=analysis_id,
        task_id=task_id,
        insights=insights,
        sources=sources,
        confidence_score=Decimal("0.7"),
        analysis_version="1.0",
        created_at=datetime.now(timezone.utc),
        report=FakeReport(
            generated_at=datetime.now(timezone.utc),
            html_content="<html>demo</html>",
        ),
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
async def test_phase2_integration_generates_gtm_plans() -> None:
    settings.enable_market_report = True  # type: ignore[attr-defined]

    task = _fake_task_basic()
    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={"r/homegym": 100000},
        cache_ttl_seconds=60,
        target_analysis_version="1.0",
    )

    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
        config=config,
    )

    payload = await service.get_report(task.id, task.user_id)
    me = payload.metadata.market_enhancements or {}
    gtm = me.get("gtm_plans") or {}
    assert isinstance(gtm, dict) and gtm
    first = next(iter(gtm.values()))
    assert isinstance(first, dict)
    assert "actions" in first and len(first["actions"]) >= 6
    # 合规提示可选（moderation_score=0.5 默认不触发），结构稳定即可
