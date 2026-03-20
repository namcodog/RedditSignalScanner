from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.report.report_runtime_helpers import (
    coerce_runtime_report_html,
    fetch_runtime_community_member_count,
    format_runtime_analysis_version,
)


def test_coerce_runtime_report_html_wraps_plain_text() -> None:
    html = coerce_runtime_report_html("plain text")
    assert "<p>" in html or "<pre>" in html


@pytest.mark.asyncio
async def test_fetch_runtime_community_member_count_falls_back_to_configured_counts() -> None:
    repository = SimpleNamespace()
    count = await fetch_runtime_community_member_count(
        "r/test",
        repository=repository,
        configured_member_counts={"r/test": 1234},
    )
    assert count == 1234


def test_format_runtime_analysis_version_handles_none() -> None:
    assert format_runtime_analysis_version(None) == "unknown"
