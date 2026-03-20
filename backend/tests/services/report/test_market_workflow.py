from __future__ import annotations

import pytest

from app.services.report.market_workflow import build_controlled_markdown_result


@pytest.mark.asyncio
async def test_build_controlled_markdown_result_prefers_community_market() -> None:
    async def _build_market_markdown():
        return "# market-md", None, None, True

    def _render_summary():
        return "# summary-md", {"overall": 0.9}

    result = await build_controlled_markdown_result(
        blocked_by_quality_gate=False,
        inline_llm_enabled=True,
        prefer_market_markdown=False,
        build_market_markdown=_build_market_markdown,
        render_controlled_summary=_render_summary,
    )

    assert result.markdown == "# market-md"
    assert result.source == "community_market"
    assert result.llm_used is True
    assert result.metrics_data == {}


@pytest.mark.asyncio
async def test_build_controlled_markdown_result_falls_back_to_summary() -> None:
    async def _build_market_markdown():
        return None, None, None, False

    def _render_summary():
        return "# summary-md", {"entity_coverage": {"overall": 0.8}}

    result = await build_controlled_markdown_result(
        blocked_by_quality_gate=False,
        inline_llm_enabled=True,
        prefer_market_markdown=False,
        build_market_markdown=_build_market_markdown,
        render_controlled_summary=_render_summary,
    )

    assert result.markdown == "# summary-md"
    assert result.source == "executive_summary"
    assert result.llm_used is False
    assert result.metrics_data == {"entity_coverage": {"overall": 0.8}}
