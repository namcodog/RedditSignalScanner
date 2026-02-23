from __future__ import annotations

from app.services.topic_profiles import TopicProfile
from app.services import analysis_engine as analysis_engine_module


def _profile() -> TopicProfile:
    return TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="desc",
        vertical="Ecommerce_Business",
        allowed_communities=["r/shopify", "r/facebookads", "r/entrepreneur"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS"],
        exclude_keywords_any=[],
        require_context_for_fetch=True,
        context_keywords_any=["ROAS"],
    )


def test_required_entity_anchor_filter_drops_posts_without_shopify() -> None:
    posts = [
        {"title": "Notion vs Evernote: better alternative to ROAS?", "summary": "random tool talk"},
        {"title": "Shopify ROAS unstable", "summary": "Need help with campaign setup"},
    ]
    filtered = analysis_engine_module._apply_topic_profile_required_filter(  # type: ignore[attr-defined]
        posts, _profile()
    )
    assert len(filtered) == 1
    assert "shopify" in str(filtered[0].get("title", "")).lower()


def test_required_entity_anchor_can_be_implied_by_subreddit_name_for_brand_subreddits() -> None:
    profile = _profile()
    posts = [
        # 在 r/shopify 这种品牌社区里，“Shopify”往往不会重复写在标题里，但仍然属于同一赛道盘子。
        {"subreddit": "r/shopify", "title": "ROAS dropped hard", "summary": "Need advice"},
        # 在非品牌社区里，仍然必须显式提到 Shopify，否则就是泛广告讨论（会跑偏）。
        {"subreddit": "r/facebookads", "title": "ROAS dropped hard", "summary": "Need advice"},
    ]
    filtered = analysis_engine_module._apply_topic_profile_required_filter(  # type: ignore[attr-defined]
        posts, profile
    )
    assert len(filtered) == 1
    assert str(filtered[0].get("subreddit") or "").lower() == "r/shopify"


def test_context_filter_is_strict_when_require_context_for_fetch_enabled() -> None:
    profile = _profile()
    posts = [
        {"title": "Shopify store speed issue", "summary": "no ads context here"},
        {"title": "Shopify theme help", "summary": "still no ads context"},
        {"title": "Shopify ROAS dropped", "summary": "this one is on-topic"},
        {"title": "Shopify app bug", "summary": "no ads context"},
        {"title": "Shopify inventory", "summary": "no ads context"},
        {"title": "Shopify payments", "summary": "no ads context"},
        {"title": "Shopify checkout", "summary": "no ads context"},
        {"title": "Shopify shipping", "summary": "no ads context"},
        {"title": "Shopify customer support", "summary": "no ads context"},
        {"title": "Shopify theme liquid", "summary": "no ads context"},
    ]
    # 只有 1/10 命中 ROAS。以前会触发“<20% 回退”，导致把 10 条全放回去 → 跑偏。
    filtered = analysis_engine_module._apply_topic_profile_context_filter(posts, profile)  # type: ignore[attr-defined]
    assert len(filtered) == 1
    assert "roas" in str(filtered[0].get("title", "")).lower()
