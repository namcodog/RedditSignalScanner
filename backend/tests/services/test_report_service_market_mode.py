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


def _fake_task_basic() -> FakeTask:
    task_id = uuid4()
    analysis_id = uuid4()

    insights = {
        "pain_points": [
            {
                "description": "订阅费太贵",
                "frequency": 3,
                "sentiment_score": -0.5,
            }
        ],
        "competitors": [],
        "opportunities": [],
        "action_items": [
            {
                "problem_definition": "订阅费陷阱",
                "evidence_chain": [
                    {
                        "title": "case A",
                        "url": "https://reddit.com/a",
                        "note": "用户在讨论订阅费负担",
                    }
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
async def test_report_service_market_mode_uses_market_template() -> None:
    old_enable_llm_summary = settings.enable_llm_summary
    old_llm_model_name = settings.llm_model_name
    old_quality_level = getattr(settings, "report_quality_level", "standard")

    try:
        # 测试必须稳定：禁用外部 LLM，强制本地路径
        settings.enable_llm_summary = False
        settings.llm_model_name = "local-extractive"
        settings.report_quality_level = "basic"  # 跳过 premium/standard 额外分支

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
        assert payload.report_html is not None
        # Controlled Executive Summary v2 模板标题（markdown→html）
        assert "执行摘要" in payload.report_html
    finally:
        settings.enable_llm_summary = old_enable_llm_summary
        settings.llm_model_name = old_llm_model_name
        settings.report_quality_level = old_quality_level


@pytest.mark.asyncio
async def test_report_service_respects_facts_v2_quality_gate_when_blocked() -> None:
    task = _fake_task_basic()
    assert task.analysis is not None
    assert task.analysis.report is not None

    # 模拟 facts_v2 质量闸门拦截：ReportService 不应生成“正常报告”，而应直接返回拦截页
    task.analysis.sources["report_tier"] = "X_blocked"
    task.analysis.sources["analysis_blocked"] = "quality_gate_blocked"
    task.analysis.sources["facts_v2_quality"] = {
        "passed": False,
        "tier": "X_blocked",
        "flags": ["topic_mismatch"],
        "metrics": {"on_topic_ratio": 0.0},
    }
    task.analysis.report.html_content = "<html>BLOCKED</html>"

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
    assert payload.report_html is not None
    assert "BLOCKED" in payload.report_html
    assert "市场洞察报告 v1" not in payload.report_html


@pytest.mark.asyncio
async def test_report_service_includes_structured_report() -> None:
    task = _fake_task_basic()
    assert task.analysis is not None
    task.analysis.sources["report_structured"] = {
        "decision_cards": [
            {
                "title": "需求趋势",
                "conclusion": "讨论热度持续稳定",
                "details": ["样本集中在核心社区", "热度集中且稳定"],
            }
        ],
        "market_health": {
            "competition_saturation": {
                "level": "中等",
                "details": ["讨论量稳定", "社区覆盖有限"],
                "interpretation": "仍有空间但需差异化。",
            },
            "ps_ratio": {
                "ratio": "1.2:1",
                "conclusion": "问题略多于答案",
                "interpretation": "用户仍在找可靠方案。",
                "health_assessment": "机会窗口仍在。",
            },
        },
        "battlefields": [],
        "pain_points": [],
        "drivers": [],
        "opportunities": [],
    }

    repo = FakeRepository(task)
    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
    )

    payload = await service.get_report(task.id, task.user_id)
    assert payload.report_structured == task.analysis.sources["report_structured"]


@pytest.mark.asyncio
async def test_report_service_prefers_structured_report_for_html() -> None:
    task = _fake_task_basic()
    assert task.analysis is not None
    task.analysis.report.html_content = "<html>OLD</html>"
    task.analysis.sources["facts_slice"] = {
        "aggregates": {
            "communities": [
                {"name": "r/test", "posts": 3, "comments": 5},
            ]
        }
    }
    task.analysis.sources["report_structured"] = {
        "decision_cards": [
            {
                "title": "需求趋势",
                "conclusion": "讨论热度持续稳定",
                "details": ["样本集中在核心社区", "热度集中且稳定"],
            },
            {
                "title": "难题与攻略比",
                "conclusion": "求助更多",
                "details": ["新手求助多", "经验分享少"],
            },
            {
                "title": "核心社群",
                "conclusion": "核心讨论集中在少数社区",
                "details": ["r/test 是高频社区", "讨论集中"],
            },
            {
                "title": "落地机会",
                "conclusion": "可以从结算与费用切入",
                "details": ["透明费用", "回款周期优化"],
            },
        ],
        "market_health": {
            "competition_saturation": {
                "level": "中等",
                "details": ["讨论量稳定", "社区覆盖有限"],
                "interpretation": "仍有空间但需差异化。",
            },
            "ps_ratio": {
                "ratio": "1.2:1",
                "conclusion": "问题略多于答案",
                "interpretation": "用户仍在找可靠方案。",
                "health_assessment": "机会窗口仍在。",
            },
        },
        "battlefields": [],
        "pain_points": [],
        "drivers": [],
        "opportunities": [],
    }

    repo = FakeRepository(task)
    service = ReportService(
        db=None,  # type: ignore[arg-type]
        repository=repo,
        cache=None,
    )

    payload = await service.get_report(task.id, task.user_id)
    assert payload.report_html is not None
    assert "需求趋势" in payload.report_html
    assert "OLD" not in payload.report_html


@pytest.mark.asyncio
async def test_report_service_generates_structured_report_inline_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _fake_task_basic()
    assert task.analysis is not None
    task.analysis.sources.pop("report_structured", None)
    task.analysis.sources["facts_slice"] = {
        "trend_summary": {"summary": "讨论热度稳定"},
        "market_saturation": {"level": "medium"},
    }

    from app.core.config import settings as _cfg

    old_inline = _cfg.enable_report_inline_llm
    old_llm_summary = _cfg.enable_llm_summary
    old_model = _cfg.llm_model_name
    old_key = getattr(_cfg, "openai_api_key", None)

    _cfg.enable_report_inline_llm = True
    _cfg.enable_llm_summary = True
    _cfg.llm_model_name = "x-ai/grok-4.1-fast"
    _cfg.openai_api_key = "test-key"

    from app.services.llm.clients.openai_client import OpenAIChatClient

    def _fake_chat_completion(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return """{\"decision_cards\": [], \"market_health\": {\"competition_saturation\": {\"level\": \"中等\", \"details\": [\"讨论量稳定\"], \"interpretation\": \"仍有空间\"}, \"ps_ratio\": {\"ratio\": \"1.2:1\", \"conclusion\": \"问题略多于答案\", \"interpretation\": \"用户仍在找可靠方案\", \"health_assessment\": \"机会窗口仍在\"}}, \"battlefields\": [], \"pain_points\": [], \"drivers\": [], \"opportunities\": []}"""

    monkeypatch.setattr(OpenAIChatClient, "_chat_completion", _fake_chat_completion)

    try:
        repo = FakeRepository(task)
        service = ReportService(
            db=None,  # type: ignore[arg-type]
            repository=repo,
            cache=None,
        )

        payload = await service.get_report(task.id, task.user_id)
        assert payload.report_structured is not None
        assert payload.report_structured["market_health"]["ps_ratio"]["ratio"] == "1.2:1"
    finally:
        _cfg.enable_report_inline_llm = old_inline
        _cfg.enable_llm_summary = old_llm_summary
        _cfg.llm_model_name = old_model
        _cfg.openai_api_key = old_key
