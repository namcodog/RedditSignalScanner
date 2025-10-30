from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.services.report_service import ReportService, ReportServiceConfig


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


def _fake_task_with_insufficient_evidence_and_blacklist() -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()

    # 行动项只有1条可点击URL证据
    insights = {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
        "action_items": [
            {
                "problem_definition": "Export is unreliable",
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
    }

    sources = {
        "communities": ["r/noise", "r/startups"],
        "posts_analyzed": 15,
        "cache_hit_rate": 0.8,
        "communities_detail": [
            {
                "name": "r/noise",  # 在 backend/config/community_blacklist.yaml 中被列入黑名单
                "categories": ["misc"],
                "mentions": 20,
                "daily_posts": 100,
                "avg_comment_length": 60,
                "cache_hit_rate": 0.9,
                "from_cache": True,
            },
            {
                "name": "r/startups",
                "categories": ["startup"],
                "mentions": 10,
                "daily_posts": 100,
                "avg_comment_length": 60,
                "cache_hit_rate": 0.9,
                "from_cache": True,
            },
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
async def test_p1_rules_insufficient_evidence_and_blacklist_filter() -> None:
    task = _fake_task_with_insufficient_evidence_and_blacklist()
    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={"r/startups": 1200000, "r/noise": 1000},
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

    # 证据不足时，建议动作包含降级标注
    ai = payload.report.action_items[0]
    assert any("证据不足" in s for s in ai.suggested_actions)
    # 概览中 recovery_applied 应包含 insufficient_evidence
    assert payload.metadata.recovery_applied and "insufficient_evidence" in payload.metadata.recovery_applied

    # 黑名单社区不应出现在 Top 列表
    top_names = [c.name for c in payload.overview.top_communities]
    assert "r/noise" not in top_names
    assert "r/startups" in top_names

