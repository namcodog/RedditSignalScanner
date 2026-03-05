import pytest
from unittest.mock import MagicMock

from app.services.report.report_service import ReportService
from app.services.analysis.t1_clustering import PainCluster
from app.services.analysis.t1_stats import (
    AspectBreakdown,
    BrandPainCooccurrence,
    CommunityStat,
    T1StatsSnapshot,
)


@pytest.mark.asyncio
async def test_build_t1_market_report_md(monkeypatch):
    stats = T1StatsSnapshot(
        generated_at="2025-11-22T00:00:00Z",
        since_utc="2024-11-22T00:00:00Z",
        subreddits=["amazonseller", "etsy"],
        global_ps_ratio=1.2,
        community_stats=[
            CommunityStat(subreddit="amazonseller", posts=100, comments=200, ps_ratio=1.1),
            CommunityStat(subreddit="etsy", posts=90, comments=150, ps_ratio=1.0),
        ],
        aspect_breakdown=[AspectBreakdown(aspect="price", pain=10, total=20)],
        brand_pain_cooccurrence=[
            BrandPainCooccurrence(brand="paypal", mentions=5, aspects=["price"]),
        ],
    )
    clusters = [
        PainCluster(
            topic="费用/订阅不透明",
            size=5,
            aspects=["price"],
            top_keywords=["fee", "charge"],
            sample_comments=["fees too high"],
        )
    ]

    async def fake_stats(_session, **_kwargs):
        return stats

    async def fake_clusters(_session, **_kwargs):
        return clusters

    monkeypatch.setattr("app.services.report.report_service.build_stats_snapshot", fake_stats)
    monkeypatch.setattr("app.services.report.report_service.build_pain_clusters", fake_clusters)

    # Force market mode on
    monkeypatch.setattr("app.services.report.report_service.settings.enable_market_report", True)
    monkeypatch.setattr("app.services.report.report_service.settings.report_mode", "market")

    svc = ReportService(db=None, repository=MagicMock(), cache=MagicMock())
    md, _stats, _clusters, llm_used = await svc._build_t1_market_report_md()  # type: ignore[attr-defined]

    assert md is not None
    assert "跨境电商支付解决方案" in md
    assert "已分析赛道" in md
    assert llm_used in {True, False}
