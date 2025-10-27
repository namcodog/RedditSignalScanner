from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.services.report_service import (
    InMemoryReportCache,
    ReportService,
    ReportServiceConfig,
)


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
class FakeTask:
    id: UUID
    user_id: UUID
    status: TaskStatus
    analysis: Optional[FakeAnalysis]
    product_description: Optional[str] = None
    user: Optional["FakeUser"] = None


@dataclass
class FakeUser:
    id: UUID
    membership_level: MembershipLevel


class FakeRepository:
    def __init__(self, task: FakeTask) -> None:
        self._task = task
        self.call_count = 0

    async def get_task_with_analysis(self, task_id: UUID) -> FakeTask | None:
        self.call_count += 1
        if task_id == self._task.id:
            return self._task
        return None


class InstrumentedReportService(ReportService):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.validation_calls = 0

    def _validate_analysis_payload(self, analysis: Any):  # type: ignore[override]
        self.validation_calls += 1
        return super()._validate_analysis_payload(analysis)


def _build_fake_task(
    version: Any = "0.9",
    membership_level: MembershipLevel = MembershipLevel.PRO,
) -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()
    insights = {
        "pain_points": [
            {
                "description": "反馈系统缓慢",
                "frequency": 5,
                "sentiment_score": -0.65,
            }
        ],
        "competitors": [],
        "opportunities": [],
    }
    sources = {
        "communities": ["r/startups"],
        "posts_analyzed": 10,
        "cache_hit_rate": 0.5,
    }
    analysis = FakeAnalysis(
        id=analysis_id,
        task_id=task_id,
        insights=insights,
        sources=sources,
        confidence_score=Decimal("0.8"),
        analysis_version=version,
        created_at=datetime.now(timezone.utc),
        report=FakeReport(
            generated_at=datetime.now(timezone.utc),
            html_content="<html>demo</html>",
        ),
    )
    fake_user = FakeUser(id=uuid4(), membership_level=membership_level)

    return FakeTask(
        id=task_id,
        user_id=uuid4(),
        status=TaskStatus.COMPLETED,
        analysis=analysis,
        product_description="Demo",
        user=fake_user,
    )


@pytest.mark.asyncio
async def test_report_service_cache_hits_without_revalidation() -> None:
    task = _build_fake_task()
    repo = FakeRepository(task)
    cache = InMemoryReportCache(ttl_seconds=3600)
    config = ReportServiceConfig(
        community_members={"r/startups": 1200000},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )

    service = InstrumentedReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=cache,
        config=config,
    )

    await service.get_report(task.id, task.user_id)
    assert service.validation_calls == 1

    await service.get_report(task.id, task.user_id)
    assert service.validation_calls == 1, "cached response should bypass validation"
    assert repo.call_count == 2, "repository still accessed for auth checks"


@pytest.mark.asyncio
async def test_report_service_migrates_old_versions() -> None:
    task = _build_fake_task(version="0.9")
    repo = FakeRepository(task)
    cache = InMemoryReportCache(ttl_seconds=3600)
    config = ReportServiceConfig(
        community_members={"r/startups": 1200000},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )

    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=cache,
        config=config,
    )

    payload = await service.get_report(task.id, task.user_id)
    assert payload.metadata.analysis_version == "1.0"
    migrated_pain_point = payload.report.pain_points[0]
    assert migrated_pain_point.severity == "high"
