from __future__ import annotations

import sys
from types import ModuleType
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


def _install_phase1_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    # app.services.analysis.persona_generator
    mod_p = ModuleType("app.services.analysis.persona_generator")

    class PersonaGenerator:  # type: ignore
        def __init__(self, llm_client=None) -> None:  # noqa: ANN001
            self._llm = llm_client
        async def generate_batch(self, db, communities, pain_points):  # noqa: ANN001
            return [
                {
                    "community": (communities or ["r/unk"])[0],
                    "persona_label": "DIY用户",
                    "traits": ["在乎性价比"],
                    "strategy": "痛点切入",
                    "confidence": 0.7,
                    "method": "rules",
                }
            ]

    mod_p.PersonaGenerator = PersonaGenerator  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.persona_generator"] = mod_p

    # app.services.analysis.quote_extractor
    mod_q = ModuleType("app.services.analysis.quote_extractor")

    class QuoteExtractor:  # type: ignore
        def extract_from_pain_points(self, pain_points):  # noqa: ANN001
            return [
                {
                    "pain_description": (pain_points or [{"description": "痛点"}])[0][
                        "description"
                    ],
                    "user_voice": "硬件已经很贵，为什么还要每月付费？",
                    "source_community": "r/homegym",
                    "sentiment_score": -0.6,
                    "confidence": 0.6,
                }
            ]

    mod_q.QuoteExtractor = QuoteExtractor  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.quote_extractor"] = mod_q

    # app.services.analysis.saturation_matrix
    mod_s = ModuleType("app.services.analysis.saturation_matrix")

    class SaturationMatrix:  # type: ignore
        async def compute(self, db, communities, brands):  # noqa: ANN001
            return [
                {
                    "community": (communities or ["r/unk"])[0],
                    "brands": [
                        {
                            "brand": (brands or ["GenericBrand"])[0],
                            "saturation": 0.5,
                            "status": "中等",
                        }
                    ],
                    "overall_saturation": 0.5,
                }
            ]

    mod_s.SaturationMatrix = SaturationMatrix  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.saturation_matrix"] = mod_s


@pytest.mark.asyncio
async def test_phase1_parallel_integration_collects_results(monkeypatch: pytest.MonkeyPatch) -> None:
    # enable feature flag for Phase 1 integration path
    settings.enable_market_report = True  # type: ignore[attr-defined]
    _install_phase1_stubs(monkeypatch)

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
    assert payload.metadata.market_enhancements is not None
    me = payload.metadata.market_enhancements or {}
    # 三类并行结果都应产生（被桩替换）
    assert isinstance(me.get("personas"), list) and len(me.get("personas")) >= 1
    assert isinstance(me.get("quotes"), list) and len(me.get("quotes")) >= 1
    assert isinstance(me.get("saturation"), list) and len(me.get("saturation")) >= 1


@pytest.mark.asyncio
async def test_phase1_parallel_integration_degrades_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    # enable feature flag for Phase 1 integration path
    settings.enable_market_report = True  # type: ignore[attr-defined]

    # Persona raises, others OK
    import sys
    from types import ModuleType

    mod_p = ModuleType("app.services.analysis.persona_generator")

    class PersonaGenerator:  # type: ignore
        def __init__(self, llm_client=None) -> None:  # noqa: ANN001
            pass

        async def generate_batch(self, db, communities, pain_points):  # noqa: ANN001
            raise RuntimeError("persona failed")

    mod_p.PersonaGenerator = PersonaGenerator  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.persona_generator"] = mod_p

    # keep quotes and saturation minimal working
    mod_q = ModuleType("app.services.analysis.quote_extractor")

    class QuoteExtractor:  # type: ignore
        def extract_from_pain_points(self, pain_points):  # noqa: ANN001
            return [
                {
                    "pain_description": (pain_points or [{"description": "痛点"}])[0][
                        "description"
                    ],
                    "user_voice": "硬件已经很贵，为什么还要每月付费？",
                    "source_community": "r/homegym",
                    "sentiment_score": -0.6,
                    "confidence": 0.6,
                }
            ]

    mod_q.QuoteExtractor = QuoteExtractor  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.quote_extractor"] = mod_q

    mod_s = ModuleType("app.services.analysis.saturation_matrix")

    class SaturationMatrix:  # type: ignore
        async def compute(self, db, communities, brands):  # noqa: ANN001
            return [
                {
                    "community": (communities or ["r/unk"])[0],
                    "brands": [
                        {
                            "brand": (brands or ["GenericBrand"])[0],
                            "saturation": 0.5,
                            "status": "中等",
                        }
                    ],
                    "overall_saturation": 0.5,
                }
            ]

    mod_s.SaturationMatrix = SaturationMatrix  # type: ignore[attr-defined]
    sys.modules["app.services.analysis.saturation_matrix"] = mod_s

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
    assert payload.metadata.market_enhancements is not None
    me = payload.metadata.market_enhancements or {}
    # personas 为空（失败降级），其余两类仍产生
    assert isinstance(me.get("personas"), list) and len(me.get("personas")) == 0
    assert isinstance(me.get("quotes"), list) and len(me.get("quotes")) >= 1
    assert isinstance(me.get("saturation"), list) and len(me.get("saturation")) >= 1
