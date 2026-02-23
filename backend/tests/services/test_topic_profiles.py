from __future__ import annotations

from pathlib import Path

from app.services.topic_profiles import (
    TopicProfile,
    build_fetch_keywords,
    build_search_keywords,
    filter_items_by_profile_context,
    filter_relevance_map_with_profile,
    load_topic_profiles,
    match_topic_profile,
    normalize_subreddit,
    topic_profile_allows_community,
)


def test_normalize_subreddit_adds_prefix_and_lowercases() -> None:
    assert normalize_subreddit("Shopify") == "r/shopify"
    assert normalize_subreddit("r/FacebookAds") == "r/facebookads"


def test_match_topic_profile_matches_by_topic_name() -> None:
    profile = TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=["r/shopify"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
    )
    assert match_topic_profile("Shopify Traffic Ads Conversion", [profile]) == profile


def test_filter_relevance_map_with_profile_keeps_only_allowed_and_patterns() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=["r/shopify", "r/facebookads"],
        community_patterns=["ppc"],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
    )
    relevance_map = {
        "r/cooking": 999,
        "r/facebookads": 10,
        "ppc": 7,  # missing r/ prefix in DB sometimes
    }
    filtered = filter_relevance_map_with_profile(relevance_map, profile, boost_allowed_to=10000)
    assert "r/cooking" not in filtered
    assert filtered["r/shopify"] == 10000
    assert filtered["r/facebookads"] == 10000
    assert filtered["r/ppc"] == 7


def test_build_search_keywords_keeps_anchor_terms_first_and_dedupes() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=[],
        community_patterns=[],
        required_entities_any=["Shopify", "store", "website"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS", "conversion rate", "Shopify"],
        exclude_keywords_any=[],
    )
    keywords = build_search_keywords(profile, topic="Shopify Traffic Ads Conversion")
    # "store"/"website" should be dropped as anchor stopwords.
    assert keywords[0].lower() == "shopify"
    assert "store" not in {k.lower() for k in keywords}
    assert "website" not in {k.lower() for k in keywords}
    # Ensure dedupe keeps only one "shopify"
    assert [k.lower() for k in keywords].count("shopify") == 1


def test_topic_profile_allows_community_by_allowed_list_or_pattern() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=["r/shopify"],
        community_patterns=["facebookads"],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
    )
    assert topic_profile_allows_community(profile, "r/shopify") is True
    assert topic_profile_allows_community(profile, "r/facebookads") is True
    assert topic_profile_allows_community(profile, "r/cooking") is False


def test_load_topic_profiles_reads_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "topic_profiles.yaml"
    yaml_path.write_text(
        """
topic_profiles:
  - id: demo
    topic_name: Demo Topic
    product_desc: Demo Desc
    vertical: demo_vertical
    allowed_communities: [r/demo]
    required_entities_any: [Shopify, store]
        """.strip(),
        encoding="utf-8",
    )
    profiles = load_topic_profiles(yaml_path)
    assert len(profiles) == 1
    assert profiles[0].id == "demo"
    assert profiles[0].allowed_communities == ["r/demo"]
    # "store" should be filtered from required_entities_any
    assert profiles[0].required_entities_any == ["Shopify"]


def test_load_topic_profiles_reads_optional_thresholds(tmp_path: Path) -> None:
    yaml_path = tmp_path / "topic_profiles.yaml"
    yaml_path.write_text(
        """
topic_profiles:
  - id: demo
    topic_name: Demo Topic
    product_desc: Demo Desc
    vertical: demo_vertical
    mode: operations
    allowed_communities: [r/demo]
    required_entities_any: [Shopify]
    include_keywords_any: [ROAS, CPC]
    preferred_days: 730
    pain_min_mentions: 5
    pain_min_unique_authors: 3
    brand_min_mentions: 3
    brand_min_unique_authors: 2
    min_solutions: 3
    require_context_for_fetch: true
    context_keywords_any: [ROAS, campaign]
        """.strip(),
        encoding="utf-8",
    )
    profiles = load_topic_profiles(yaml_path)
    assert len(profiles) == 1
    p = profiles[0]
    assert p.preferred_days == 730
    assert p.pain_min_mentions == 5
    assert p.pain_min_unique_authors == 3
    assert p.brand_min_mentions == 3
    assert p.brand_min_unique_authors == 2
    assert p.min_solutions == 3
    assert p.mode == "operations"
    assert p.require_context_for_fetch is True
    assert p.context_keywords_any == ["ROAS", "campaign"]


def test_build_fetch_keywords_prefers_context_and_drops_anchor_terms() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=[],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS", "conversion rate", "traffic"],
        exclude_keywords_any=[],
        require_context_for_fetch=True,
    )
    kw = build_fetch_keywords(profile, topic="Shopify Traffic Ads Conversion")
    # Anchor term should not be in fetch keywords when require_context_for_fetch is enabled.
    assert "shopify" not in {k.lower() for k in kw}
    assert kw[0].lower() in {"roas", "conversion rate", "traffic"}


def test_filter_items_by_profile_context_keeps_only_context_hits_when_enabled() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=[],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS"],
        exclude_keywords_any=[],
        require_context_for_fetch=True,
        context_keywords_any=["ROAS"],
    )
    items = [
        {"title": "Shopify theme issue", "text": "help pls"},
        {"title": "Shopify ROAS dropped hard", "text": "need advice"},
    ]
    kept = filter_items_by_profile_context(items, profile, text_keys=("title", "text"))
    assert len(kept) == 1
    assert "roas" in (kept[0].get("title") or "").lower()


def test_filter_items_by_profile_context_checks_all_text_fields() -> None:
    profile = TopicProfile(
        id="p",
        topic_name="t",
        product_desc="desc",
        vertical="ecommerce_business",
        allowed_communities=[],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS"],
        exclude_keywords_any=[],
        require_context_for_fetch=True,
        context_keywords_any=["ROAS"],
    )
    items = [
        {
            "title": "Shopify theme issue",
            "body": "My ROAS dropped hard after the update",
        }
    ]
    kept = filter_items_by_profile_context(items, profile, text_keys=("title", "body"))
    assert len(kept) == 1
