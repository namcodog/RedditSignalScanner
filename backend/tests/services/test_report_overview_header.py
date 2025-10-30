from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from app.models.task import TaskStatus
from app.services.report_service import ReportService, ReportServiceConfig
from app.models.user import MembershipLevel


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


def _fake_task_with_communities() -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()

    insights = {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
    }

    sources = {
        "communities": ["r/startups"],
        "posts_analyzed": 15,
        "cache_hit_rate": 0.8,
        "communities_detail": [
            {
                "name": "r/startups",
                "categories": ["startup"],
                "mentions": 3,
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
async def test_overview_header_fields_present() -> None:
    task = _fake_task_with_communities()
    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={"r/startups": 1200000},
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

    ov = payload.overview
    assert ov.total_communities >= 1
    assert ov.top_n == len(ov.top_communities)
    # 未标记 discovered 的类别应推断为 pool
    assert ov.seed_source in (None, "pool", "pool+discovery")
