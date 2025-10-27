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


@pytest.mark.asyncio
async def test_version_migration_adds_missing_fields() -> None:
    """测试版本迁移添加缺失字段"""
    task_id = uuid4()
    analysis_id = uuid4()

    # 创建 0.9 版本的数据（缺少 severity, example_posts, user_examples）
    insights = {
        "pain_points": [
            {
                "description": "性能问题",
                "frequency": 10,
                "sentiment_score": -0.8,
                # 缺少 severity, example_posts, user_examples
            }
        ],
        "competitors": [],
        "opportunities": [],
    }
    sources = {
        "communities": ["r/programming"],
        "posts_analyzed": 50,
        "cache_hit_rate": 0.7,
        "analysis_duration": 15.5,  # 旧字段名
        # 缺少 analysis_duration_seconds
    }

    analysis = FakeAnalysis(
        id=analysis_id,
        task_id=task_id,
        insights=insights,
        sources=sources,
        confidence_score=Decimal("0.85"),
        analysis_version="0.9",
        created_at=datetime.now(timezone.utc),
        report=FakeReport(
            generated_at=datetime.now(timezone.utc),
            html_content="<html>test</html>",
        ),
    )

    task = FakeTask(
        id=task_id,
        user_id=uuid4(),
        status=TaskStatus.COMPLETED,
        analysis=analysis,
        product_description="测试产品",
        user=FakeUser(id=uuid4(), membership_level=MembershipLevel.PRO),
    )

    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )

    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
        config=config,
    )

    payload = await service.get_report(task.id, task.user_id)

    # 验证版本已升级
    assert payload.metadata.analysis_version == "1.0"

    # 验证新增字段
    pain_point = payload.report.pain_points[0]
    assert pain_point.severity == "high"  # 基于 sentiment_score -0.8
    assert pain_point.example_posts == []
    assert pain_point.user_examples == []


@pytest.mark.asyncio
async def test_version_migration_preserves_existing_data() -> None:
    """测试版本迁移保留现有数据"""
    task_id = uuid4()
    analysis_id = uuid4()

    insights = {
        "pain_points": [
            {
                "description": "原有描述",
                "frequency": 20,
                "sentiment_score": -0.5,
            }
        ],
        "competitors": [{"name": "竞品A", "mentions": 5}],
        "opportunities": [{"description": "机会点", "impact": "high"}],
    }
    sources = {
        "communities": ["r/test1", "r/test2"],
        "posts_analyzed": 100,
        "cache_hit_rate": 0.9,
        "analysis_duration": 30.0,
    }

    analysis = FakeAnalysis(
        id=analysis_id,
        task_id=task_id,
        insights=insights,
        sources=sources,
        confidence_score=Decimal("0.9"),
        analysis_version="0.9",
        created_at=datetime.now(timezone.utc),
        report=FakeReport(
            generated_at=datetime.now(timezone.utc),
            html_content="<html>preserved</html>",
        ),
    )

    task = FakeTask(
        id=task_id,
        user_id=uuid4(),
        status=TaskStatus.COMPLETED,
        analysis=analysis,
        product_description="测试产品",
        user=FakeUser(id=uuid4(), membership_level=MembershipLevel.PRO),
    )

    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )

    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
        config=config,
    )

    payload = await service.get_report(task.id, task.user_id)

    # 验证原有数据未被破坏
    assert payload.report.pain_points[0].description == "原有描述"
    assert payload.report.pain_points[0].frequency == 20
    assert len(payload.report.competitors) == 1
    assert len(payload.report.opportunities) == 1


@pytest.mark.asyncio
async def test_version_migration_skips_if_already_target() -> None:
    """测试如果已经是目标版本则跳过迁移"""
    task = _build_fake_task(version="1.0")  # 已经是目标版本
    repo = FakeRepository(task)
    config = ReportServiceConfig(
        community_members={},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )

    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
        config=config,
    )

    payload = await service.get_report(task.id, task.user_id)

    # 版本应保持不变
    assert payload.metadata.analysis_version == "1.0"


@pytest.mark.asyncio
async def test_severity_classification() -> None:
    """测试 severity 分类逻辑"""
    test_cases = [
        (-0.8, "high"),      # 强负面
        (-0.5, "medium"),    # 中等负面
        (-0.2, "low"),       # 轻微负面
        (0.0, "low"),        # 中性
        (0.5, "low"),        # 正面（不应该出现在 pain_points，但测试边界）
    ]

    for sentiment_score, expected_severity in test_cases:
        task_id = uuid4()
        insights = {
            "pain_points": [
                {
                    "description": f"测试 {sentiment_score}",
                    "frequency": 1,
                    "sentiment_score": sentiment_score,
                }
            ],
            "competitors": [],
            "opportunities": [],
        }
        sources = {
            "communities": ["r/test"],
            "posts_analyzed": 10,
            "cache_hit_rate": 0.5,
        }

        analysis = FakeAnalysis(
            id=uuid4(),
            task_id=task_id,
            insights=insights,
            sources=sources,
            confidence_score=Decimal("0.8"),
            analysis_version="0.9",
            created_at=datetime.now(timezone.utc),
            report=FakeReport(
                generated_at=datetime.now(timezone.utc),
                html_content="<html>test</html>",
            ),
        )

        task = FakeTask(
            id=task_id,
            user_id=uuid4(),
            status=TaskStatus.COMPLETED,
            analysis=analysis,
            user=FakeUser(id=uuid4(), membership_level=MembershipLevel.PRO),
        )

        repo = FakeRepository(task)
        config = ReportServiceConfig(
            community_members={},
            cache_ttl_seconds=3600,
            target_analysis_version="1.0",
        )

        service = ReportService(
            db=None,  # type: ignore[arg-type]
            repository=repo,
            cache=None,
            config=config,
        )

        payload = await service.get_report(task.id, task.user_id)
        assert payload.report.pain_points[0].severity == expected_severity
