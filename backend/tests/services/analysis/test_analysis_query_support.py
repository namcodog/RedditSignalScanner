from __future__ import annotations

from types import SimpleNamespace

from app.services.analysis.analysis_query_support import (
    apply_keyword_stopwords,
    apply_query_focus_filter,
    apply_topic_profile_required_filter,
    augment_keywords,
    build_reddit_search_queries,
    extract_keywords,
    filter_posts_by_blocklist,
)


def test_extract_and_augment_keywords_bridge_cn_terms() -> None:
    keywords = extract_keywords("帮我研究新生儿夜奶记录协作工具")
    augmented = augment_keywords(keywords, "帮我研究新生儿夜奶记录协作工具")

    assert "新生儿夜奶记录协作工具".lower() not in augmented
    assert "baby" in augmented
    assert "feeding" in augmented
    assert "sleep" in augmented


def test_build_reddit_search_queries_filters_non_ascii_and_dedupes() -> None:
    queries = build_reddit_search_queries(
        tokens=["paypal", "fees", "到账", "fees", "risk"],
        lookback_days=365,
    )

    assert queries == ["paypal fees risk", "paypal fees"]


def test_apply_keyword_stopwords_prefers_blacklist_contract() -> None:
    blacklist = SimpleNamespace(
        semantic_expansion_stopwords={"help"},
        filter_keywords={"review"},
    )

    filtered = apply_keyword_stopwords(
        ["PayPal", "help", "review", "fees", "reddit", "product"],
        blacklist,
    )

    assert filtered == ["PayPal", "fees"]


def test_apply_topic_profile_required_filter_accepts_brand_subreddit_anchor() -> None:
    profile = SimpleNamespace(required_entities_any=["shopify"])
    posts = [
        {"id": "p1", "subreddit": "Shopify", "title": "ROAS dropped", "summary": ""},
        {"id": "p2", "subreddit": "marketing", "title": "ROAS dropped", "summary": ""},
    ]

    kept = apply_topic_profile_required_filter(posts, profile)

    assert [post["id"] for post in kept] == ["p1"]


def test_apply_query_focus_filter_and_blocklist_keep_relevant_posts() -> None:
    posts = [
        {"id": "p1", "title": "PayPal payout still pending", "summary": "fees and payout"},
        {"id": "p2", "title": "General ecommerce chat", "summary": "nothing about payout"},
        {"id": "p3", "title": "PayPal payout still pending", "summary": "marketplace listing"},
    ]

    focused = apply_query_focus_filter(
        posts,
        "帮跨境卖家看清 PayPal 手续费和回款延迟",
        keywords=["paypal", "fees", "payout"],
        open_topic_route=None,
    )
    filtered = filter_posts_by_blocklist(focused, ["marketplace listing"])

    assert [post["id"] for post in filtered] == ["p1"]


def test_augment_keywords_does_not_leak_ai_terms_from_pet_hair_home_query() -> None:
    augmented = augment_keywords(
        [],
        "我想研究 home cleaning、vacuum、organization、storage 这些家庭清洁和收纳场景里的真实麻烦，尤其是灰尘、pet hair、small space 和 cleaning routine，判断有没有工具机会。",
    )

    assert "cleaning" in augmented
    assert "vacuum" in augmented
    assert "storage" in augmented
    assert "ai" not in augmented
    assert "ml" not in augmented
    assert "machine" not in augmented


def test_augment_keywords_for_generic_edc_query_does_not_force_flashlight_branch() -> None:
    augmented = augment_keywords(
        [],
        "我想做 EDC 配件方向，想知道 Reddit 上关于收纳、携带、口袋组织这类真实麻烦里，有没有能直接切入的产品机会。",
    )

    assert "edc" in augmented
    assert "carry" in augmented
    assert "organizer" in augmented
    assert "flashlight" not in augmented
    assert "multitool" not in augmented


def test_augment_keywords_bridges_open_topic_commerce_problem_to_english_anchors() -> None:
    augmented = augment_keywords(
        [],
        "卖成人用品时，最卡下单成交的地方是什么？我想看看到底是支付、审核还是信任问题卡住了转化。",
    )

    assert "checkout" in augmented
    assert "conversion" in augmented
    assert "payment" in augmented
    assert "compliance" in augmented
    assert "trust" in augmented
    assert "ecommerce" in augmented

    queries = build_reddit_search_queries(tokens=augmented, lookback_days=365)
    assert queries
