from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.schemas.analysis import AnalysisRead
from app.schemas.report_payload import ReportPayload
from app.services.report.render_bundle import ReportRenderBundle
from app.services.report.report_payload_builder import (
    ReportPayloadBuildInput,
    build_report_payload,
)


def _build_analysis() -> AnalysisRead:
    return AnalysisRead.model_validate(
        {
            "id": uuid4(),
            "task_id": uuid4(),
            "insights": {
                "pain_points": [
                    {
                        "description": "物流慢",
                        "frequency": 4,
                        "sentiment_score": -0.7,
                        "severity": "high",
                        "example_posts": [],
                        "user_examples": [],
                    }
                ],
                "competitors": [],
                "opportunities": [],
                "action_items": [],
                "entity_summary": {"brands": [], "features": [], "pain_points": []},
                "pain_clusters": [],
                "competitor_layers_summary": [],
                "channel_breakdown": [],
                "top_drivers": [],
                "market_saturation": [],
                "battlefield_profiles": [],
            },
            "sources": {
                "communities": ["r/startups"],
                "posts_analyzed": 10,
                "cache_hit_rate": 0.5,
                "product_description": "测试产品",
                "communities_detail": [
                    {
                        "name": "r/startups",
                        "categories": ["business"],
                        "mentions": 5,
                        "daily_posts": 10,
                        "avg_comment_length": 120,
                        "cache_hit_rate": 0.8,
                        "from_cache": False,
                    }
                ],
            },
            "confidence_score": Decimal("0.82"),
            "analysis_version": "1.0",
            "created_at": datetime.now(timezone.utc),
        }
    )


@pytest.mark.asyncio
async def test_build_report_payload_uses_render_bundle_and_updates_metadata() -> None:
    analysis = _build_analysis()
    task = SimpleNamespace(
        id=analysis.task_id,
        status=TaskStatus.COMPLETED,
        product_description="测试产品",
        analysis=SimpleNamespace(report=SimpleNamespace(html_content="<html>old</html>")),
    )

    async def _fake_fetch_member_count(_community: str) -> int:
        return 123456

    payload = await build_report_payload(
        build_input=ReportPayloadBuildInput(
            task=task,
            analysis=analysis,
            generated_at=datetime.now(timezone.utc),
            action_items=[],
            render_bundle=ReportRenderBundle(
                report_html="<html><body>new</body></html>",
                metrics_summary=None,
                llm_used=True,
                controlled_md_source="community_market",
                market_enhancements={"mode": "community_market"},
            ),
        ),
        fetch_member_count=_fake_fetch_member_count,
    )

    assert isinstance(payload, ReportPayload)
    assert payload.report_html == "<html><body>new</body></html>"
    assert payload.metadata.llm_used is True
    assert payload.metadata.market_enhancements == {"mode": "community_market"}
    assert payload.overview.top_communities[0].members == 123456

