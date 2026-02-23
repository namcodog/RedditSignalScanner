from datetime import datetime, timezone

from app.services.report.t1_market_agent import ReportInputs, T1MarketReportAgent
from app.services.t1_clustering import PainCluster
from app.services.t1_stats import (
    AspectBreakdown,
    BrandPainCooccurrence,
    CommunityStat,
    T1StatsSnapshot,
)


def test_market_agent_renders_markdown_sections() -> None:
    stats = T1StatsSnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        since_utc=datetime.now(timezone.utc).isoformat(),
        subreddits=["amazonseller", "etsy"],
        global_ps_ratio=1.2,
        community_stats=[
            CommunityStat(subreddit="amazonseller", posts=1000, comments=75000, ps_ratio=1.3),
            CommunityStat(subreddit="etsy", posts=900, comments=40000, ps_ratio=1.1),
        ],
        aspect_breakdown=[
            AspectBreakdown(aspect="price", pain=120, total=200),
            AspectBreakdown(aspect="subscription", pain=80, total=120),
        ],
        brand_pain_cooccurrence=[
            BrandPainCooccurrence(brand="paypal", mentions=30, aspects=["price"]),
            BrandPainCooccurrence(brand="stripe", mentions=20, aspects=["subscription"]),
        ],
    )
    clusters = [
        PainCluster(
            topic="费用/订阅不透明",
            size=5,
            aspects=["price"],
            top_keywords=["fee", "charge", "fx"],
            sample_comments=["fees are too high", "charges unclear"],
        ),
        PainCluster(
            topic="账期与冻结/锁定",
            size=3,
            aspects=["subscription"],
            top_keywords=["hold", "frozen"],
            sample_comments=["payout held", "freeze funds"],
        ),
    ]
    markdown = T1MarketReportAgent(ReportInputs(stats=stats, clusters=clusters)).render()

    assert "已分析赛道" in markdown
    assert "决策卡片" in markdown
    assert "用户痛点" in markdown
    assert "商业机会" in markdown
    assert "r/amazonseller" in markdown
