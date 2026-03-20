from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.report.analysis_payload_loader import (
    format_analysis_version,
    validate_report_analysis_payload,
)


def _fake_analysis(*, version: str = "0.9"):
    return SimpleNamespace(
        id=uuid4(),
        task_id=uuid4(),
        insights={
            "pain_points": [
                {
                    "description": "手续费太高，汇损很难懂",
                    "sentiment_score": -0.72,
                    "frequency": 8,
                }
            ],
            "competitors": [],
            "opportunities": [
                {
                    "description": "提供更透明的汇率说明",
                    "relevance_score": 0.72,
                    "potential_users": "中小卖家",
                }
            ],
            "entity_summary": {
                "channels": [
                    {"name": "Reddit", "mentions": 12},
                ]
            },
        },
        sources={
            "communities": ["r/demo"],
            "posts_analyzed": 12,
            "cache_hit_rate": 0.2,
            "analysis_duration": 12.4,
            "report_tier": "A_full",
            "unknown_legacy_key": "drop-me",
        },
        confidence_score=Decimal("0.8"),
        analysis_version=version,
        created_at=datetime.now(timezone.utc),
    )


def test_validate_report_analysis_payload_migrates_and_normalizes_v09() -> None:
    payload = validate_report_analysis_payload(
        analysis=_fake_analysis(),
        target_analysis_version="1.0",
    )

    assert payload.analysis_version == "1.0"
    assert payload.insights.pain_points[0].severity == "high"
    assert payload.insights.pain_points[0].text == "手续费太高，汇损很难懂"
    assert payload.insights.opportunities[0].title
    assert payload.sources.analysis_duration_seconds == 12
    assert payload.sources.report_tier == "A_full"


def test_validate_report_analysis_payload_filters_unknown_source_keys_and_builds_channels() -> None:
    payload = validate_report_analysis_payload(
        analysis=_fake_analysis(version="1.0"),
        target_analysis_version="1.0",
    )

    dumped = payload.sources.model_dump()
    assert "unknown_legacy_key" not in dumped
    assert payload.insights.channel_breakdown
    assert payload.insights.channel_breakdown[0].name == "Reddit"


def test_format_analysis_version_keeps_one_decimal_for_integers() -> None:
    assert format_analysis_version("1") == "1.0"
    assert format_analysis_version(2) == "2.0"
    assert format_analysis_version("1.25") == "1.25"
