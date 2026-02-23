from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.facts_v2.midstream import (
    compute_brand_pain_v2,
    compute_pain_clusters_v2,
    compute_source_range,
    filter_solutions_by_profile,
)
from app.services.topic_profiles import TopicProfile


def _dt(day: int) -> str:
    return datetime(2025, 12, day, 0, 0, 0, tzinfo=timezone.utc).isoformat()


def test_compute_source_range_counts_actual_items() -> None:
    posts = [
        {"post_id": "t3_p1", "created_at": _dt(1), "subreddit": "r/shopify"},
        {"post_id": "t3_p2", "created_at": _dt(2), "subreddit": "r/facebookads"},
    ]
    comments = [
        {"quote_id": "t1_c1", "created_at": _dt(3), "subreddit": "r/facebookads"},
    ]
    assert compute_source_range(posts=posts, comments=comments) == {"posts": 2, "comments": 1}


def test_pain_clusters_have_metrics_and_evidence() -> None:
    profile = TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="面向 Shopify 卖家的广告优化与转化率提升工具",
        vertical="Ecommerce_Business",
        allowed_communities=["r/shopify", "r/facebookads", "r/PPC"],
        community_patterns=["shopify", "facebookads", "ppc", "advertising"],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads", "Google Ads"],
        include_keywords_any=["ROAS", "CPC", "conversion", "ad spend"],
        exclude_keywords_any=["recipe", "cake", "cook"],
    )
    domain_config = {
        "marketing": {
            "subreddits": ["r/facebookads", "r/ppc"],
            "pain_keywords": {
                "price": ["roas low", "budget wasted"],
                "function": ["cpc high", "conversion low", "pixel not firing"],
                "service": ["ad account banned"],
            },
        }
    }
    comments = [
        {
            "quote_id": "t1_c1",
            "comment_id": "t1_c1",
            "post_id": "t3_p1",
            "author_id": "u_1",
            "subreddit": "r/facebookads",
            "created_at": _dt(3),
            "text": "My Shopify store ROAS is low and CPC is high on Facebook Ads.",
            "comment_score": 12,
        },
        {
            "quote_id": "t1_c2",
            "comment_id": "t1_c2",
            "post_id": "t3_p2",
            "author_id": "u_2",
            "subreddit": "r/facebookads",
            "created_at": _dt(4),
            "text": "CPC high again. ROAS low. Any Shopify ads tips?",
            "comment_score": 5,
        },
    ]
    posts: list[dict[str, object]] = []

    clusters = compute_pain_clusters_v2(
        posts=posts,
        comments=comments,
        profile=profile,
        domain_pain_config=domain_config,
        max_clusters=5,
        min_mentions=1,
        min_unique_authors=1,
        max_evidence=3,
    )
    assert clusters
    first = clusters[0]
    assert first["title"]
    assert isinstance(first["metrics"]["mentions"], int) and first["metrics"]["mentions"] >= 1
    assert isinstance(first["metrics"]["unique_authors"], int) and first["metrics"]["unique_authors"] >= 1
    assert first["evidence_quote_ids"]


def test_brand_pain_unique_authors_not_zero_when_mentions_positive() -> None:
    profile = TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="面向 Shopify 卖家的广告优化与转化率提升工具",
        vertical="Ecommerce_Business",
        allowed_communities=["r/shopify", "r/facebookads"],
        community_patterns=["shopify", "facebookads"],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS", "CPC"],
        exclude_keywords_any=["cake", "cook"],
    )
    domain_config = {
        "marketing": {
            "subreddits": ["r/facebookads"],
            "pain_keywords": {"price": ["roas low"]},
        }
    }
    comments = [
        {
            "quote_id": "t1_c1",
            "comment_id": "t1_c1",
            "post_id": "t3_p1",
            "author_id": "u_1",
            "subreddit": "r/facebookads",
            "created_at": _dt(3),
            "text": "Shopify ROAS low on Facebook Ads.",
            "comment_score": 10,
        },
        {
            "quote_id": "t1_c2",
            "comment_id": "t1_c2",
            "post_id": "t3_p2",
            "author_id": "u_2",
            "subreddit": "r/facebookads",
            "created_at": _dt(4),
            "text": "My Shopify ROAS low too. Facebook Ads killing me.",
            "comment_score": 8,
        },
    ]
    posts: list[dict[str, object]] = []

    clusters = compute_pain_clusters_v2(
        posts=posts,
        comments=comments,
        profile=profile,
        domain_pain_config=domain_config,
        max_clusters=3,
        min_mentions=1,
        min_unique_authors=1,
        max_evidence=5,
    )
    brand_candidates = ["Shopify", "Facebook Ads"]
    brand_pain = compute_brand_pain_v2(
        posts=posts,
        comments=comments,
        profile=profile,
        pain_clusters=clusters,
        brand_candidates=brand_candidates,
        min_mentions=1,
        min_unique_authors=1,
        min_evidence=1,
        max_items=10,
        max_evidence=3,
    )
    assert brand_pain
    shopify = next((row for row in brand_pain if row["brand"].lower() == "shopify"), None)
    assert shopify is not None
    assert shopify["mentions"] >= 1
    assert shopify["unique_authors"] >= 1
    assert shopify["evidence_quote_ids"]


def test_filter_solutions_by_profile_drops_offtopic() -> None:
    profile = TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="面向 Shopify 卖家的广告优化与转化率提升工具",
        vertical="Ecommerce_Business",
        allowed_communities=["r/facebookads"],
        community_patterns=["facebookads"],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS", "CPC", "conversion"],
        exclude_keywords_any=["cake", "recipe"],
    )
    solutions = [
        {"description": "Seriously, just pause all your Facebook ads for now"},
        {"description": "Can I just brag about the red sauce I made last night"},
        {"description": "On Shopify, switch to CAPI to fix attribution and improve ROAS"},
    ]
    filtered = filter_solutions_by_profile(solutions, profile=profile, max_items=10)
    descriptions = [row["description"] for row in filtered]
    assert any("facebook ads" in d.lower() for d in descriptions)
    assert any("shopify" in d.lower() for d in descriptions)
    assert not any("red sauce" in d.lower() for d in descriptions)
