from __future__ import annotations

from app.services.hotpost.reddit_search_spec_builder import build_reddit_search_specs


def test_paid_economics_search_first_keeps_both_source_modes() -> None:
    specs = build_reddit_search_specs("business-growth-ops")
    paid = [item for item in specs if item.topic_pack_id == "paid-economics"]
    listing = [item for item in paid if item.mode == "listing"]
    search = [item for item in paid if item.mode == "search"]

    assert listing
    assert search
    assert set(dict.fromkeys(item.subreddit for item in search)) >= {
        "PPC",
        "FacebookAds",
        "googleads",
        "ecommerce",
        "analytics",
    }
    assert any(item.query == "blended cac" for item in search)
    assert any(item.query == "cutting paid spend what happened" for item in search)


def test_tools_efficiency_adds_open_source_tail_surface_without_losing_workflow_queries() -> None:
    specs = build_reddit_search_specs("ai-automation")
    tools = [item for item in specs if item.topic_pack_id == "tools-efficiency"]
    listing = [item for item in tools if item.mode == "listing"]
    search = [item for item in tools if item.mode == "search"]
    open_source = [item for item in tools if item.topic_cluster_id == "open-source-projects"]
    workflow = [item for item in tools if item.topic_cluster_id == "workflow-friction" and item.mode == "search"]

    assert listing
    assert search
    assert {item.subreddit for item in listing if item.topic_cluster_id == "open-source-projects"} == {
        "DeepSeek",
        "opencodeCLI",
        "claudeskills",
        "OpenWebUI",
        "vibecoding",
    }
    assert {item.subreddit for item in open_source if item.mode == "search"} == {
        "DeepSeek",
        "opencodeCLI",
        "LocalLLaMA",
        "OpenSourceAI",
        "ClaudeCode",
        "AI_Agents",
        "claudeskills",
        "OpenWebUI",
        "vibecoding",
        "AgentsOfAI",
    }
    assert {item.subreddit for item in workflow[:6]} == {
        "ChatGPT",
        "ClaudeAI",
        "OpenAI",
        "cursor",
        "vibecoding",
        "selfhosted",
    }
    assert workflow[0].query == "tool switching fatigue"
    assert any(item.query == "tool switching fatigue" for item in workflow)
    assert any(item.query == "which ai tool did you keep" for item in workflow)
    assert any(item.query == "ai workflow with fewer tools" for item in workflow)
    assert any(item.query == "how do i keep context across ai tools" for item in workflow)


def test_selection_signals_search_first_keeps_wider_surface() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    selection = [item for item in specs if item.topic_pack_id == "selection-signals"]
    listing = [item for item in selection if item.mode == "listing"]
    search = [item for item in selection if item.mode == "search"]

    assert not listing
    assert search
    assert search[0].query == "sheds everywhere"
    assert "petproducts" in {item.subreddit for item in search}
    assert "CatAdvice" not in {item.subreddit for item in search}
    assert "ManyBaggers" in {item.subreddit for item in search}
    assert any(item.query == "better alternative for pet owners" for item in search)


def test_cluster_segments_stop_pet_queries_from_spraying_into_edc_subreddits() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    selection = [item for item in specs if item.topic_pack_id == "selection-signals" and item.mode == "search"]

    assert not any(
        item.subreddit == "ManyBaggers" and item.query == "sheds everywhere"
        for item in selection
    )
    assert any(
        item.subreddit == "petproducts" and item.query == "sheds everywhere"
        for item in selection
    )
    pet_spec = next(
        item for item in selection if item.subreddit == "petproducts" and item.query == "sheds everywhere"
    )
    assert pet_spec.topic_cluster_id == "pet"
    assert pet_spec.topic_cluster_ids == ["pet"]


def test_small_goods_segment_prefers_scenario_queries_before_problem_queries() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    small_goods = [
        item
        for item in specs
        if item.topic_pack_id == "selection-signals"
        and item.mode == "search"
        and item.topic_cluster_id == "small-goods"
    ]

    assert small_goods[:3]
    assert [item.query for item in small_goods[:3]] == [
        "cheap useful accessory",
        "cheap useful accessory",
        "cheap useful accessory",
    ]
    assert [item.subreddit for item in small_goods[:3]] == [
        "Frugal",
        "BuyItForLife",
        "homeowners",
    ]
    assert all(item.query != "too commoditized" for item in small_goods[:6])


def test_category_winds_listing_first_uses_seller_direction_surface() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    category = [item for item in specs if item.topic_pack_id == "category-winds"]
    listing = [item for item in category if item.mode == "listing"]
    search = [item for item in category if item.mode == "search"]

    assert listing
    assert search
    assert category[0].mode == "listing"
    assert search[0].query == "saturated niche amazon"
    assert {item.subreddit for item in search[:5]} == {
        "AmazonSeller",
        "FulfillmentByAmazon",
        "EtsySellers",
        "EntrepreneurRideAlong",
        "sidehustle",
    }
    assert any(item.query == "what niche still has room" for item in search)
    assert any(item.query == "how do i find an ecommerce category that still has room" for item in search)


def test_agent_builder_stays_search_only_for_reliability_signals() -> None:
    specs = build_reddit_search_specs("ai-automation")
    agent = [item for item in specs if item.topic_pack_id == "agent-builder"]
    listing = [item for item in agent if item.mode == "listing"]
    search = [item for item in agent if item.mode == "search"]

    assert not listing
    assert {item.subreddit for item in search[:6]} == {"ChatGPTCoding", "ClaudeAI", "OpenAI", "cursor", "automation", "mcp"}
    assert agent[0].mode == "search"
    assert search[0].query == "agent broke in production"
    assert any(item.query == "stopped using agent framework" for item in search)
    assert any(item.query == "agent eval" for item in search)
    assert any(item.query == "why is it so hard to trust an agent in production" for item in search)
    assert all(item.query != "llm" for item in search)


def test_upstream_winds_listing_avoids_claudecode_discussion_noise() -> None:
    specs = build_reddit_search_specs("ai-automation")
    upstream_listing = [item for item in specs if item.topic_pack_id == "upstream-winds" and item.mode == "listing"]

    assert upstream_listing
    assert "ClaudeCode" not in {item.subreddit for item in upstream_listing}
    assert "OpenAI" in {item.subreddit for item in upstream_listing}
    assert "claude" in {item.subreddit for item in upstream_listing}
    assert "Anthropic" in {item.subreddit for item in upstream_listing}


def test_search_templates_expand_reddit_sentence_patterns() -> None:
    ai_specs = build_reddit_search_specs("ai-automation")
    ai_tools = [item for item in ai_specs if item.topic_pack_id == "tools-efficiency" and item.mode == "search"]
    assert any(item.query == "how do i keep context across ai tools" for item in ai_tools)

    ecommerce_specs = build_reddit_search_specs("ecommerce-sellers")
    selection = [item for item in ecommerce_specs if item.topic_pack_id == "selection-signals" and item.mode == "search"]
    assert any(item.query == "what do you use for clean pet hair in a small apartment" for item in selection)
    category = [item for item in ecommerce_specs if item.topic_pack_id == "category-winds" and item.mode == "search"]
    assert any(item.query == "how do i find an ecommerce category that still has room" for item in category)

    growth_specs = build_reddit_search_specs("business-growth-ops")
    paid = [item for item in growth_specs if item.topic_pack_id == "paid-economics" and item.mode == "search"]
    assert any(item.query == "how do i know if paid ads are actually profitable" for item in paid)
    organic = [item for item in growth_specs if item.topic_pack_id == "organic-discovery" and item.mode == "search"]
    assert organic == []


def test_growth_bridge_packs_stop_using_search_first_queries() -> None:
    specs = build_reddit_search_specs("business-growth-ops")

    organic = [item for item in specs if item.topic_pack_id == "organic-discovery"]
    funnel = [item for item in specs if item.topic_pack_id == "funnel-conversion"]

    assert organic
    assert funnel
    assert {item.mode for item in organic} == {"listing"}
    assert {item.mode for item in funnel} == {"listing"}
    assert all(item.primary_reason == "organic-discovery:listing_keyword_bridge" for item in organic)
    assert all(item.primary_reason == "funnel-conversion:listing_keyword_bridge" for item in funnel)
    assert [item.topic_pack_id for item in specs[:6]] == [
        "organic-discovery",
        "organic-discovery",
        "organic-discovery",
        "organic-discovery",
        "organic-discovery",
        "organic-discovery",
    ]


def test_growth_bridge_packs_include_new_round_communities() -> None:
    specs = build_reddit_search_specs("business-growth-ops")
    organic = [item for item in specs if item.topic_pack_id == "organic-discovery"]
    funnel = [item for item in specs if item.topic_pack_id == "funnel-conversion"]

    assert "seogrowth" in {item.subreddit for item in organic}
    assert "Substack" in {item.subreddit for item in organic}
    assert "b2bmarketing" in {item.subreddit for item in funnel}


def test_selection_signals_include_new_round_tail_communities() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    selection = [item for item in specs if item.topic_pack_id == "selection-signals" and item.mode == "search"]

    assert {"backpacking", "flashlight", "Ultralight"} <= {item.subreddit for item in selection if item.topic_cluster_id == "outdoor"}
    assert {"homeoffice", "battlestations", "ultrawidemasterrace", "MouseReview"} <= {
        item.subreddit for item in selection if item.topic_cluster_id == "desk-setup"
    }
    assert "beyondthebump" in {item.subreddit for item in selection if item.topic_cluster_id == "parenting-travel"}


def test_selection_signals_include_stationery_and_planner_tail_communities() -> None:
    specs = build_reddit_search_specs("ecommerce-sellers")
    selection = [item for item in specs if item.topic_pack_id == "selection-signals" and item.mode == "search"]

    assert {"stationery", "planners", "Journaling"} <= {
        item.subreddit for item in selection if item.topic_cluster_id == "paper-goods-and-gifting"
    }
    assert {"hobonichi", "fountainpens", "GiftIdeas"} <= {
        item.subreddit for item in selection if item.topic_cluster_id == "paper-goods-and-gifting"
    }


def test_funnel_conversion_includes_service_business_tail_communities() -> None:
    specs = build_reddit_search_specs("business-growth-ops")
    funnel = [item for item in specs if item.topic_pack_id == "funnel-conversion"]

    assert "consulting" in {item.subreddit for item in funnel}
    assert "sales" in {item.subreddit for item in funnel}


def test_scope_spec_budget_is_lower_than_old_explosion() -> None:
    counts = {
        scope: len(build_reddit_search_specs(scope))
        for scope in ("ai-automation", "ecommerce-sellers", "business-growth-ops")
    }

    assert counts["ai-automation"] < 900
    assert counts["ecommerce-sellers"] < 800
    assert counts["business-growth-ops"] < 1400


def test_experimental_communities_are_excluded_from_default_specs() -> None:
    specs = build_reddit_search_specs("business-growth-ops")

    assert not any(item.is_experimental_probe for item in specs)


def test_experimental_communities_require_explicit_flag_and_small_budget() -> None:
    default_specs = build_reddit_search_specs("ecommerce-sellers")
    expanded_specs = build_reddit_search_specs("ecommerce-sellers", include_experimental=True)
    experimental = [item for item in expanded_specs if item.is_experimental_probe]

    assert len(expanded_specs) > len(default_specs)
    assert experimental
    assert {item.subreddit for item in experimental} <= {
        "HerOneBag",
        "bikepacking",
        "trailrunning",
        "CampingandHiking",
    }
    assert len({item.subreddit.lower() for item in experimental}) <= 4
