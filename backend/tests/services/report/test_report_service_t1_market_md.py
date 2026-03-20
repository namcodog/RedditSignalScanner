import pytest

from app.services.analysis.t1_clustering import PainCluster
from app.services.analysis.t1_stats import (
    AspectBreakdown,
    BrandPainCooccurrence,
    CommunityStat,
    T1StatsSnapshot,
)
from app.services.report.market_workflow import build_market_report_markdown


@pytest.mark.asyncio
async def test_build_t1_market_report_md(monkeypatch):
    stats = T1StatsSnapshot(
        generated_at="2025-11-22T00:00:00Z",
        since_utc="2024-11-22T00:00:00Z",
        subreddits=["amazonseller", "etsy"],
        global_ps_ratio=1.2,
        total_pain=52,
        total_solution=33,
        community_stats=[
            CommunityStat(
                subreddit="amazonseller",
                posts=100,
                comments=200,
                ps_ratio=1.1,
                pain_count=30,
                solution_count=18,
                recent_posts_30d=15,
                recent_comments_30d=45,
            ),
            CommunityStat(
                subreddit="etsy",
                posts=90,
                comments=150,
                ps_ratio=1.0,
                pain_count=22,
                solution_count=15,
                recent_posts_30d=12,
                recent_comments_30d=33,
            ),
        ],
        aspect_breakdown=[AspectBreakdown(aspect="price", pain=10, total=20)],
        brand_pain_cooccurrence=[
            BrandPainCooccurrence(
                brand="paypal",
                mentions=5,
                aspects=["price"],
                unique_authors=3,
                evidence_comment_ids=["e1"],
            ),
        ],
    )
    clusters = [
        PainCluster(
            topic="费用/订阅不透明",
            size=5,
            aspects=["price"],
            keywords=["fee", "charge"],
            samples=["fees too high"],
        )
    ]

    async def fake_stats(_session, **_kwargs):
        return stats

    async def fake_clusters(_session, **_kwargs):
        return clusters

    monkeypatch.setattr("app.services.report.market_workflow.build_stats_snapshot", fake_stats)
    monkeypatch.setattr("app.services.report.market_workflow.build_pain_clusters", fake_clusters)

    md, _stats, _clusters, llm_used = await build_market_report_markdown(
        None,
        quality_level="standard",
        product_description="跨境电商支付解决方案",
        analysis_payload=None,
    )

    assert md is not None
    assert "跨境电商支付解决方案" in md
    assert "已分析赛道" in md
    assert llm_used in {True, False}
