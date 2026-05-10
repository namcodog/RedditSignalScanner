from __future__ import annotations

from pathlib import Path

from app.services.community.community_recommendation_models import CommunitySignal
from app.services.community.community_recommendation_service import (
    build_community_recommendation_report_from_signals,
)
from app.services.community.interest_tag_catalog import load_interest_tag_catalog


SERVICE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "community"
    / "community_recommendation_service.py"
)


def test_report_service_is_read_only_application_boundary() -> None:
    source = SERVICE_SOURCE.read_text(encoding="utf-8")

    assert "SessionFactory" not in source
    assert "community_pool_phase2_dev_writer" not in source
    assert "community_governance_audit" not in source
    assert ".commit(" not in source


def test_report_service_builds_preview_audit_payloads_and_summary() -> None:
    signals = [
        CommunitySignal(
            community="r/ClaudeCode",
            keywords=("claude", "agent"),
            semantic_terms=("agent workflow",),
            hotpost_cards=3,
            recent_posts_15d=2,
        )
    ]

    report = build_community_recommendation_report_from_signals(
        signals,
        tag_limit=10,
        community_limit=5,
    )

    assert len(report.preview.tags) == len(load_interest_tag_catalog().tags)
    assert report.audit.row_count == report.recommendation_count
    assert report.summary["db_writes"] is False
    assert report.summary["user_input_required"] is False
    assert report.preview_payload()["tags"]
    assert report.audit_payload()["row_count"] == report.recommendation_count
