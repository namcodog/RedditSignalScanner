from __future__ import annotations

from app.services.analysis.analysis_engine import _build_reddit_search_queries


def test_build_reddit_search_queries_filters_non_ascii_and_keeps_anchor() -> None:
    queries = _build_reddit_search_queries(
        tokens=["面向", "Shopify", "ROAS", "ad account", "卖家的广告优化与转化率提升工具"],
        lookback_days=730,
    )
    assert queries
    assert any("shopify" in q.lower() for q in queries)
    assert all("面向" not in q for q in queries)
    assert all("卖家的广告优化与转化率提升工具" not in q for q in queries)
