from __future__ import annotations

import pytest

from scripts.acceptance.run_live_hotpost_acceptance import (
    REQUIRED_HOTPOST_PATHS,
    _required_hotpost_paths_missing,
    _validate_hotpost_payload,
)


def test_required_hotpost_paths_missing_accepts_complete_openapi() -> None:
    payload = {
        "paths": {path: {} for path in REQUIRED_HOTPOST_PATHS},
    }

    assert _required_hotpost_paths_missing(payload) == []


def test_required_hotpost_paths_missing_reports_missing_routes() -> None:
    payload = {
        "paths": {
            "/api/hotpost/search": {},
            "/api/hotpost/result/{query_id}": {},
        },
    }

    missing = _required_hotpost_paths_missing(payload)

    assert "/api/hotpost/stream/{query_id}" in missing
    assert "/api/hotpost/deepdive" in missing


def test_validate_hotpost_payload_accepts_stable_response() -> None:
    payload = {
        "query_id": "demo-id",
        "status": "completed",
        "mode": "trending",
        "summary": "这波值得继续看。",
        "evidence_count": 12,
        "communities": ["r/tiktokshop", "r/shopify"],
        "top_quotes": [{"quote": "Great traction this week."}],
        "topics": [
            {
                "time_trend": "rising",
                "evidence": [{"title": "post", "url": "https://reddit.com"}],
            }
        ],
    }

    assert _validate_hotpost_payload(payload) == []


@pytest.mark.parametrize(
    ("payload", "expected_issue"),
    [
        (
            {"status": "failed", "summary": "x", "evidence_count": 1, "communities": []},
            "missing query_id",
        ),
        (
            {"query_id": "demo", "status": "queued", "summary": "x", "evidence_count": 1, "communities": []},
            "unexpected status: queued",
        ),
        (
            {"query_id": "demo", "status": "completed", "summary": "", "evidence_count": 1, "communities": []},
            "missing summary",
        ),
        (
            {"query_id": "demo", "status": "completed", "summary": "x", "communities": []},
            "missing evidence_count",
        ),
        (
            {"query_id": "demo", "status": "completed", "summary": "x", "evidence_count": -1, "communities": []},
            "negative evidence_count",
        ),
        (
            {"query_id": "demo", "status": "completed", "summary": "x", "evidence_count": 1, "communities": "r/test"},
            "communities is not a list",
        ),
        (
            {"query_id": "demo", "status": "completed", "mode": "trending", "summary": "x", "evidence_count": 1, "communities": []},
            "missing top_quotes",
        ),
    ],
)
def test_validate_hotpost_payload_rejects_invalid_response(
    payload: dict[str, object],
    expected_issue: str,
) -> None:
    issues = _validate_hotpost_payload(payload)

    assert expected_issue in issues


def test_validate_hotpost_payload_rejects_trending_without_topics() -> None:
    payload = {
        "query_id": "demo-id",
        "status": "completed",
        "mode": "trending",
        "summary": "summary",
        "evidence_count": 3,
        "communities": ["r/test"],
        "top_quotes": [{"quote": "quote"}],
    }

    issues = _validate_hotpost_payload(payload)

    assert "missing topics for trending mode" in issues


def test_validate_hotpost_payload_rejects_rant_without_voice() -> None:
    payload = {
        "query_id": "demo-id",
        "status": "completed",
        "mode": "rant",
        "summary": "summary",
        "evidence_count": 3,
        "communities": ["r/test"],
        "top_quotes": [{"quote": "quote"}],
        "pain_points": [{"category": "退款流程", "sample_quotes": [], "evidence": []}],
    }

    issues = _validate_hotpost_payload(payload)

    assert "missing user voice in rant pain_points" in issues


def test_validate_hotpost_payload_rejects_opportunity_without_market() -> None:
    payload = {
        "query_id": "demo-id",
        "status": "completed",
        "mode": "opportunity",
        "summary": "summary",
        "evidence_count": 3,
        "communities": ["r/test"],
        "top_quotes": [{"quote": "quote"}],
        "unmet_needs": [{"need": "faster checkout"}],
    }

    issues = _validate_hotpost_payload(payload)

    assert "missing market_opportunity for opportunity mode" in issues
