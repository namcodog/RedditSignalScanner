from app.services.hotpost.query_resolver import HotpostQueryResolution


def test_build_hotpost_query_plan_expands_rant_query_and_marks_noise_terms() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="shopify app bugs help",
            search_query="shopify app bugs help",
            keywords=["shopify", "app", "bugs"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_intent == "pain_point_discovery"
    assert "help" in plan.negative_terms
    assert "issue" in plan.expanded_terms
    assert "shopify" in plan.expanded_terms
    assert plan.candidate_subreddits[0] == "r/shopify"
    assert plan.search_strategy == "subreddit-first"


def test_build_hotpost_query_plan_keeps_resolution_subreddits_and_opportunity_strategy() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="opportunity",
        resolution=HotpostQueryResolution(
            original_query="scheduling tool alternative",
            search_query="scheduling tool alternative",
            keywords=["scheduling", "tool", "alternative"],
            subreddits=["r/saas"],
            source="original",
        ),
    )

    assert plan.query_intent == "opportunity_discovery"
    assert plan.candidate_subreddits[0] == "r/saas"
    assert "r/startups" in plan.candidate_subreddits
    assert plan.search_strategy == "global-first"
    assert any("looking for" in term or "alternative" in term for term in plan.expanded_terms)


def test_build_hotpost_query_plan_emits_semantic_constraints_for_opportunity() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="opportunity",
        resolution=HotpostQueryResolution(
            original_query="shopify chargeback prevention software",
            search_query="shopify chargeback prevention software",
            keywords=["shopify", "chargeback", "prevention", "software"],
            subreddits=["r/shopify"],
            source="original",
        ),
    )

    assert "software" in plan.positive_intent_terms
    assert "exam" in plan.forbidden_context_terms
    assert "shopify" in plan.domain_terms
    assert "chargeback" in plan.domain_terms
    assert "chargeback" in plan.strict_domain_terms
    assert plan.strict_anchor_min_hits == 1


def test_build_hotpost_query_plan_promotes_rant_domain_terms_to_strict_anchors() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="tiktok seller support issue",
            search_query="tiktok seller support issue",
            keywords=["tiktok", "seller", "support", "issue"],
            subreddits=[],
            source="original",
        ),
    )

    assert "support" in plan.domain_terms
    assert plan.strict_anchor_min_hits == 1
    assert any(term in plan.strict_domain_terms for term in {"tiktok", "seller", "support"})


def test_build_hotpost_query_plan_uses_resolved_query_as_rant_core_anchor() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么tiktok上做的内容有流量但却没有转化购买?",
            search_query="Why TikTok content gets traffic but no purchase conversions",
            keywords=[
                "tiktok traffic no sales",
                "tiktok high views low conversions",
                "tiktok marketing funnel",
            ],
            subreddits=["r/tiktok", "r/marketing"],
            source="llm",
        ),
    )

    assert "tiktok" in plan.core_terms
    assert "traffic" in plan.core_terms
    assert "sales" in plan.core_terms
    assert "conversions" in plan.core_terms
    assert "tiktok traffic no sales" not in plan.core_terms
    assert plan.query_family == "platform_conversion_friction"
    assert plan.primary_friction == "weak_buy_reason"
    assert plan.alias_terms == ["no sales"]
    assert plan.query_parts[0] == "tiktok ads no sales"
    assert "tiktok traffic low conversion" in plan.query_parts


def test_build_hotpost_query_plan_filters_rant_resolution_subreddits_to_direct_matches() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么tiktok上做的内容有流量但却没有转化购买?",
            search_query="Why TikTok content has traffic but no purchase conversions",
            keywords=["tiktok", "content", "traffic", "purchase", "conversions"],
            subreddits=[
                "r/tiktok",
                "r/tiktokhelp",
                "r/socialmediamarketing",
                "r/ecommerce",
                "r/marketing",
            ],
            source="llm",
        ),
    )

    assert plan.candidate_subreddits == [
        "r/tiktok",
        "r/tiktokads",
        "r/tiktokshop",
        "r/tiktokhelp",
    ]


def test_build_hotpost_query_plan_adds_platform_conversion_subreddits_without_resolution_hints() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why do tiktok views not turn into sales anymore?",
            search_query="why do tiktok views not turn into sales anymore?",
            keywords=["tiktok", "views", "sales"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "platform_conversion_friction"
    assert plan.candidate_subreddits[:4] == [
        "r/tiktok",
        "r/tiktokads",
        "r/tiktokshop",
        "r/tiktokhelp",
    ]
    assert "tiktok ads no sales" in plan.query_parts
    assert "tiktok views low conversion" in plan.query_parts
    assert "r/customerservice" not in plan.candidate_subreddits


def test_build_hotpost_query_plan_frontloads_pre_purchase_platform_queries() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why do tiktok ads get clicks but still no sales?",
            search_query="why do tiktok ads get clicks but still no sales?",
            keywords=["tiktok", "ads", "clicks", "sales"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "platform_conversion_friction"
    assert plan.query_parts[:3] == [
        "tiktok ads no sales",
        "tiktok ads tracking conversion",
        "tiktok ads checkout conversion",
    ]


def test_build_hotpost_query_plan_defers_generic_product_rant_to_subreddit_discovery() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="what do people complain most about coffee machines overall?",
            search_query="what do people complain most about coffee machines overall?",
            keywords=["people", "complain", "most", "coffee", "machines", "overall"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "generic_complaint_discovery"
    assert plan.primary_friction == "trust_gap"
    assert plan.candidate_subreddits[:2] == ["r/coffee", "r/machines"]


def test_build_hotpost_query_plan_defers_comparison_rant_to_subreddit_discovery() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="codex vs claude instruction following complaints",
            search_query="codex vs claude instruction following complaints",
            keywords=["codex", "claude", "comparison", "complaints"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "comparison_complaint_discovery"
    assert plan.candidate_subreddits[:2] == ["r/codex", "r/claude"]
    assert "r/customerservice" in plan.candidate_subreddits
    assert "r/smallbusiness" in plan.candidate_subreddits
    assert "r/codexclaude" not in plan.candidate_subreddits
    assert "r/codex_claude" not in plan.candidate_subreddits
    assert plan.search_strategy == "global-first"


def test_build_hotpost_query_plan_prefers_resolved_rant_anchor_terms_over_search_sentence_noise() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么tiktok上做的内容有流量但却没有转化购买?",
            search_query="Why TikTok content has traffic but no purchase conversions?",
            keywords=["TikTok traffic", "conversions", "TikTok purchases"],
            subreddits=["r/tiktok", "r/tiktokmarketing", "r/socialmediamarketing"],
            source="llm",
        ),
    )

    assert plan.core_terms == ["tiktok", "traffic", "conversions", "purchases"]
    assert "content" not in plan.core_terms
    assert "sales" in plan.domain_terms
    assert "sales" in plan.strict_domain_terms


def test_build_hotpost_query_plan_compacts_business_pain_query_for_rant() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="售卖成人小玩具都有什么痛点?",
            search_query="pain points selling adult sex toys",
            keywords=["adult", "sex", "toys", "selling", "pain", "points", "challenges"],
            subreddits=["r/sextoys"],
            source="llm",
        ),
    )

    assert plan.query_family == "business_friction_discovery"
    assert plan.core_terms == ["adult", "sex", "toys", "selling"]
    assert plan.query_parts[0] == "adult sex toys business challenges"


def test_build_hotpost_query_plan_drops_business_context_meta_terms_from_anchor_query() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="售卖成人小玩具都有什么痛点?",
            search_query="selling adult toys challenges",
            keywords=["adult", "toys", "seller", "marketing", "payment", "compliance", "shipping"],
            subreddits=["r/sextoys"],
            source="llm",
        ),
    )

    assert plan.query_parts[0] == "adult toys business challenges"


def test_build_hotpost_query_plan_prioritizes_business_query_for_non_platform_conversion_rant() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="卖成人用品时，最容易卡成交的地方是什么？",
            search_query="selling adult products conversion friction",
            keywords=["sex", "toys", "adult", "products", "sales", "conversion", "transaction", "friction"],
            subreddits=["r/sextoys"],
            source="llm",
        ),
    )

    assert plan.query_family == "business_friction_discovery"
    assert plan.primary_friction == "transaction_friction"
    assert plan.query_parts[0] == "sex toys adult business challenges"
    assert "sex toys no sales" in plan.query_parts


def test_build_hotpost_query_plan_keeps_business_default_communities_for_business_rant() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="售卖成人小玩具都有什么痛点?",
            search_query="selling adult toys challenges",
            keywords=["adult", "toys", "sex", "seller", "selling", "payment", "marketing"],
            subreddits=["r/sexsellers", "r/sextoys"],
            source="llm",
        ),
    )

    assert "r/smallbusiness" in plan.candidate_subreddits
    assert "r/ecommerce" in plan.candidate_subreddits
    assert "r/entrepreneur" in plan.candidate_subreddits
    assert "r/customerservice" not in plan.candidate_subreddits


def test_build_hotpost_query_plan_expands_configured_alias_terms() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="trending",
        resolution=HotpostQueryResolution(
            original_query="AIGC",
            search_query="AIGC",
            keywords=["aigc"],
            subreddits=[],
            source="original",
        ),
    )

    assert "generative ai" in plan.alias_terms
    assert "ai-generated content" in plan.expanded_terms
    assert plan.query_parts[0] == "generative ai"


def test_build_hotpost_query_plan_strips_glue_terms_from_specific_issue_rant() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why are people mad about Uber Eats delivery fees lately",
            search_query="why are people mad about Uber Eats delivery fees lately",
            keywords=["people", "mad", "uber", "eats", "delivery", "fees", "lately"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "specific_issue"
    assert plan.candidate_subreddits[:2] == ["r/uber", "r/eats"]
    assert plan.domain_terms == ["uber", "eats", "delivery", "fees"]
    assert "people" not in plan.core_terms
    assert "mad" not in plan.core_terms


def test_build_hotpost_query_plan_keeps_tool_comparison_anchor_terms_for_specific_issue() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why do people say Asana is easier to use than Jira now",
            search_query="why do people say Asana is easier to use than Jira now",
            keywords=["people", "say", "asana", "easier", "use", "jira", "now"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "specific_issue"
    assert plan.candidate_subreddits[:2] == ["r/asana", "r/jira"]
    assert "asana" in plan.core_terms
    assert "jira" in plan.core_terms
    assert "people" not in plan.domain_terms
    assert "say" not in plan.domain_terms


def test_build_hotpost_query_plan_adds_short_subject_anchor_for_ai_specific_issue() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why notion ai output is garbage",
            search_query="why notion ai output is garbage",
            keywords=["notion", "output", "garbage", "writes", "nonsense"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "specific_issue"
    assert plan.candidate_subreddits[:2] == ["r/notion", "r/notionai"]
    assert "notion ai" in plan.query_parts
    assert "notion ai output issue" in plan.query_parts
    assert len(plan.query_parts) >= 4


def test_build_hotpost_query_plan_drops_focus_word_subreddits_when_object_anchor_exists() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么 Notion AI 总把我的笔记改写成空话",
            search_query="Notion AI rewriting notes fluff",
            keywords=["notion", "rewrite", "notes", "fluff", "output", "ai"],
            subreddits=["r/notion", "r/notionai", "r/rewrite", "r/rewritehelp", "r/fluff", "r/verbose"],
            source="llm",
        ),
    )

    assert "r/notion" in plan.candidate_subreddits
    assert "r/notionai" in plan.candidate_subreddits
    assert "r/rewrite" not in plan.candidate_subreddits
    assert "r/rewritehelp" not in plan.candidate_subreddits
    assert "r/fluff" not in plan.candidate_subreddits
    assert "r/empty" not in plan.candidate_subreddits
    assert "r/verbose" not in plan.candidate_subreddits


def test_build_hotpost_query_plan_locks_comparison_to_two_sided_focus_queries() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why codex is better than claude for instruction following",
            search_query="why codex is better than claude for instruction following",
            keywords=["codex", "claude", "instruction", "following", "better"],
            subreddits=[],
            source="original",
        ),
    )

    assert plan.query_family == "comparison_complaint_discovery"
    assert plan.candidate_subreddits[:2] == ["r/codex", "r/claude"]
    assert "r/customerservice" in plan.candidate_subreddits
    assert "codex complaints" not in plan.query_parts
    assert "claude complaints" not in plan.query_parts
    assert "codex instruction following better than claude" in plan.query_parts
    assert "prefer codex over claude for instruction following" in plan.query_parts
    assert "claude instruction following worse than codex" in plan.query_parts
    assert "switched from claude to codex for instruction following" in plan.query_parts


def test_build_hotpost_query_plan_drops_length_descriptor_subreddits_for_object_rant() -> None:
    from app.services.hotpost.query_planner import build_hotpost_query_plan

    plan = build_hotpost_query_plan(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么 Notion AI 总把我的长笔记改成空洞套话",
            search_query="Notion AI poor summarization long notes",
            keywords=["notion", "long", "notes", "summarization", "generic", "ai"],
            subreddits=["r/notion", "r/notionai", "r/long", "r/notes"],
            source="llm",
        ),
    )

    assert "r/notion" in plan.candidate_subreddits
    assert "r/notionai" in plan.candidate_subreddits
    assert "r/long" not in plan.candidate_subreddits
