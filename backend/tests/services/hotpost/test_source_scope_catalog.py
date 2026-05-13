from __future__ import annotations

from app.services.hotpost.source_scope_catalog import (
    build_topic_pack_candidate_quotas,
    get_scope_topic_packs,
    get_topic_pack_keyword_buckets,
)


def test_ecommerce_scope_exposes_topic_packs() -> None:
    packs = get_scope_topic_packs("ecommerce-sellers")
    assert [pack.topic_pack_id for pack in packs] == [
        "selection-signals",
        "category-winds",
        "kill-signals",
    ]


def test_ecommerce_selection_signals_focus_on_buyer_side_sources() -> None:
    keywords = get_topic_pack_keyword_buckets("ecommerce-sellers", "selection-signals")
    packs = get_scope_topic_packs("ecommerce-sellers")
    selection = next(pack for pack in packs if pack.topic_pack_id == "selection-signals")
    flattened = [item for values in keywords.values() for item in values]
    assert "petproducts" in selection.subreddits
    assert "EDC" in selection.subreddits
    assert "CatAdvice" not in selection.subreddits
    assert "dogs" not in selection.subreddits
    assert "pet hair remover tool" in flattened
    assert "small product niche" in flattened


def test_ecommerce_topic_pack_quotas_follow_contract() -> None:
    quotas = build_topic_pack_candidate_quotas("ecommerce-sellers", 8)
    assert quotas == {
        "selection-signals": 5,
        "category-winds": 2,
        "kill-signals": 1,
    }


def test_collect_defaults_are_yaml_driven_and_wider_than_old_path() -> None:
    from app.services.hotpost.hotpost_supply_contract import get_supply_collect_defaults

    assert get_supply_collect_defaults() == {
        "max_candidates_per_scope": 24,
        "search_fetch_limit": 12,
        "listing_fetch_limit": 12,
        "comments_fetch_limit": 5,
        "comment_request_timeout": 4,
        "api_max_concurrency": 6,
        "low_quota_remaining_threshold": 12,
        "low_quota_cooldown_seconds": 20,
        "stop_comment_fetch_below_remaining": 18,
        "max_consecutive_rate_limit_errors": 3,
        "spec_batch_size": 8,
        "max_search_specs_per_scope": 120,
        "max_listing_specs_per_scope": 36,
        "subreddit_candidate_cap": 2,
        "search_subreddit_limit": 5,
        "listing_subreddit_limit": 4,
        "keywords_per_bucket": 2,
        "template_queries_per_segment": 3,
        "max_search_specs_per_segment": 40,
        "max_listing_specs_per_segment": 12,
    }


def test_growth_paid_economics_focuses_on_ads_operators_not_generic_marketing() -> None:
    keywords = get_topic_pack_keyword_buckets("business-growth-ops", "paid-economics")
    packs = get_scope_topic_packs("business-growth-ops")
    paid = next(pack for pack in packs if pack.topic_pack_id == "paid-economics")
    flattened = [item for values in keywords.values() for item in values]
    assert "marketing" not in paid.subreddits
    assert "PPC" in paid.subreddits
    assert "Google_Ads" in paid.subreddits
    assert "third party tracking" in paid.search_queries
    assert "Triple Whale" in paid.search_queries
    assert "blended cac" in flattened
    assert "cutting paid spend what happened" in flattened


def test_ai_tools_efficiency_focuses_on_workflow_friction_not_chatgpt_memes() -> None:
    keywords = get_topic_pack_keyword_buckets("ai-automation", "tools-efficiency")
    packs = get_scope_topic_packs("ai-automation")
    tools = next(pack for pack in packs if pack.topic_pack_id == "tools-efficiency")
    flattened = [item for values in keywords.values() for item in values]
    assert "artificial" not in tools.subreddits
    assert "automation" in tools.subreddits
    assert "ClaudeCode" not in tools.subreddits
    assert "ChatGPT" in tools.subreddits
    assert "cursor" in tools.subreddits
    assert "tool switching fatigue" in flattened
    assert "re explaining context to ai" in flattened
    assert "which ai subscription was worth keeping" in flattened
    assert "which ai tool did you keep" in flattened


def test_ai_scope_now_covers_product_adoption_and_key_people_routes() -> None:
    packs = get_scope_topic_packs("ai-automation")
    tools = next(pack for pack in packs if pack.topic_pack_id == "tools-efficiency")

    assert "ProductManagement" in tools.subreddits
    assert "ai product manager" in tools.search_queries
    assert "how do i ship an ai feature users actually adopt" in tools.search_queries


def test_ai_agent_builder_no_longer_absorbs_open_source_route_queries() -> None:
    packs = get_scope_topic_packs("ai-automation")
    upstream = next(pack for pack in packs if pack.topic_pack_id == "upstream-winds")
    builder = next(pack for pack in packs if pack.topic_pack_id == "agent-builder")

    assert "open source ai project" in upstream.search_queries
    assert "open sourced" in upstream.search_queries
    assert "open source ai project" not in builder.search_queries
    assert "open sourced" not in builder.search_queries


def test_ecommerce_scope_now_covers_brand_and_crowdfunding_surface() -> None:
    packs = get_scope_topic_packs("ecommerce-sellers")
    selection = next(pack for pack in packs if pack.topic_pack_id == "selection-signals")

    assert "kickstarter" in selection.subreddits
    assert "brand alternative" in selection.search_queries
    assert "how do i validate a product before a big inventory bet" in selection.search_queries


def test_growth_scope_now_covers_geo_content_and_market_intel_surface() -> None:
    packs = get_scope_topic_packs("business-growth-ops")
    organic = next(pack for pack in packs if pack.topic_pack_id == "organic-discovery")
    funnel = next(pack for pack in packs if pack.topic_pack_id == "funnel-conversion")

    assert "TechSEO" in organic.subreddits
    assert "Emailmarketing" in organic.subreddits
    assert "Copywriting" not in organic.subreddits
    assert "Beehiiv" in organic.search_queries
    assert "Google Search Console" in organic.search_queries
    assert "how do i choose between beehiiv and substack" in organic.search_queries
    assert "how do i figure out what the market actually cares about" in organic.search_queries
    assert "analytics" in funnel.subreddits
    assert "Hotjar" in funnel.search_queries
    assert "how do i find where users drop before checkout" in funnel.search_queries
