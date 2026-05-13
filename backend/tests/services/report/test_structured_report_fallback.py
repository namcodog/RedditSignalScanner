from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.report.structured_report_fallback import (
    build_structured_report_fallback,
)


def _task() -> TaskSummary:
    return TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="EDC 钥匙和口袋收纳方向",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_build_structured_report_fallback_keeps_full_contract_shape() -> None:
    report = build_structured_report_fallback(
        task=_task(),
        insights={
            "pain_points": [
                {
                    "description": "钥匙和门禁卡经常互相刮花",
                    "user_examples": ["每天拿钥匙都要找半天"],
                }
            ],
            "opportunities": [
                {
                    "description": "磁吸分区钥匙整理模块",
                    "key_insights": ["快速取放", "防刮", "口袋更平整"],
                }
            ],
            "top_drivers": [{"title": "随手可拿", "description": "拿取动作要一步到位"}],
        },
        sources={
            "posts_analyzed": 140,
            "comments_analyzed": 320,
            "ps_ratio": 1.2,
            "communities": ["r/EDC", "r/flashlight", "r/knives"],
            "communities_detail": [
                {"name": "r/EDC", "mentions": 42},
                {"name": "r/flashlight", "mentions": 21},
            ],
        },
        report_tier="A_full",
    )

    assert len(report["decision_cards"]) == 4
    assert len(report["battlefields"]) == 4
    assert len(report["pain_points"]) == 3
    assert len(report["drivers"]) == 3
    assert len(report["opportunities"]) == 2
    assert report["market_health"]["ps_ratio"]["ratio"] == "1.20"


def test_build_structured_report_fallback_for_scouting_still_has_same_shape() -> None:
    report = build_structured_report_fallback(
        task=_task(),
        insights={"pain_points": [], "opportunities": [], "top_drivers": []},
        sources={"posts_analyzed": 12, "comments_analyzed": 0, "communities": ["r/EDC"]},
        report_tier="C_scouting",
    )

    assert len(report["decision_cards"]) == 4
    assert len(report["battlefields"]) == 4
    assert len(report["pain_points"]) == 3
    assert len(report["drivers"]) == 3
    assert len(report["opportunities"]) == 2
