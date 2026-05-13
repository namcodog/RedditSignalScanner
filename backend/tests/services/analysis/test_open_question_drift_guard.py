from __future__ import annotations

from app.services.analysis.analysis_collection_support import CommunityProfile, OpenTopicRoute
from app.services.analysis.open_question_drift_guard import (
    evaluate_open_question_drift_guard,
)
from app.services.analysis.open_question_query_plan import OpenQuestionQueryPlan


def _route(*allowed_names: str, margin: float = 1.0) -> OpenTopicRoute:
    profiles = tuple(
        CommunityProfile(
            name=name,
            categories=("seed",),
            description_keywords=("checkout",),
            daily_posts=80,
            avg_comment_length=70,
            cache_hit_rate=0.5,
        )
        for name in allowed_names
    )
    return OpenTopicRoute(
        warzone="Ecommerce_Business",
        confidence=0.8,
        reasons=("seed",),
        seed_profiles=profiles,
        allowed_names=frozenset(allowed_names),
        margin=margin,
        candidate_warzones=("Ecommerce_Business", "AI_Workflow"),
    )


def test_drift_guard_relaxes_route_when_must_keep_is_missing() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=("Next.js 14", "MySQL"),
        must_not_invent=(),
        route_query_en="Next.js 14 timeout error",
        retrieve_queries_en=("next.js timeout",),
        rerank_query="Next.js 14 App Router Server Action MySQL timeout",
        route_keywords=("next.js", "timeout"),
        retrieve_keywords=("next.js", "timeout"),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=_route("r/nextjs"),
    )

    assert result.relax_route is True
    assert "must_keep_drift" in result.reasons
    assert result.diagnostics["entity_preservation_rate"] == 0.5


def test_drift_guard_relaxes_route_when_specific_entity_is_invented() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=("Next.js 14",),
        must_not_invent=(),
        route_query_en="Next.js 14 ReactNative crash",
        retrieve_queries_en=("next.js reactnative crash",),
        rerank_query="Next.js 14 build error",
        route_keywords=("next.js", "crash"),
        retrieve_keywords=("next.js", "crash"),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=_route("r/nextjs"),
    )

    assert result.relax_route is True
    assert "invented_entity" in result.reasons
    assert result.diagnostics["invented_entities"] == ["ReactNative"]


def test_drift_guard_relaxes_route_when_retrieval_points_outside_route() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=(),
        must_not_invent=(),
        route_query_en="checkout conversion orders sales",
        retrieve_queries_en=("checkout conversion orders",),
        rerank_query="卖成人用品时最卡下单成交的地方是什么",
        route_keywords=("checkout", "conversion"),
        retrieve_keywords=("checkout", "conversion"),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=_route("r/ecommerce", margin=0.1),
        search_posts=[
            {"subreddit": "wallstreetbets"},
            {"subreddit": "wallstreetbets"},
            {"subreddit": "stocks"},
            {"subreddit": "stocks"},
            {"subreddit": "stocks"},
        ],
        semantic_counts={"stocks": 4, "wallstreetbets": 2},
    )

    assert result.relax_route is True
    assert "retrieval_consistency" in result.reasons
    assert result.diagnostics["route_hits"] == 0
    assert result.diagnostics["retrieval_total"] == 5


def test_drift_guard_keeps_route_when_retrieval_supports_it() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=(),
        must_not_invent=(),
        route_query_en="checkout conversion orders sales",
        retrieve_queries_en=("checkout conversion orders",),
        rerank_query="卖成人用品时最卡下单成交的地方是什么",
        route_keywords=("checkout", "conversion"),
        retrieve_keywords=("checkout", "conversion"),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=_route("r/ecommerce", "r/shopify", margin=0.3),
        search_posts=[
            {"subreddit": "ecommerce"},
            {"subreddit": "shopify"},
            {"subreddit": "shopify"},
        ],
        semantic_counts={"shopify": 3, "ecommerce": 2},
    )

    assert result.relax_route is False
    assert result.reasons == ()
    assert result.diagnostics["route_hits"] == 3


def test_drift_guard_keeps_route_when_profile_is_in_route_warzone() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=(),
        must_not_invent=(),
        route_query_en="checkout conversion orders sales",
        retrieve_queries_en=("checkout conversion orders",),
        rerank_query="卖成人用品时最卡下单成交的地方是什么",
        route_keywords=("checkout", "conversion"),
        retrieve_keywords=("checkout", "conversion"),
    )
    route = _route("r/ecommerce", margin=0.3)
    aligned_profiles = (
        CommunityProfile(
            name="r/FacebookAds",
            categories=("warzone:Ecommerce_Business",),
            description_keywords=("ads", "shopify"),
            daily_posts=80,
            avg_comment_length=70,
            cache_hit_rate=0.5,
        ),
        CommunityProfile(
            name="r/buhaydigital",
            categories=("warzone:Ecommerce_Business",),
            description_keywords=("marketing", "ecommerce"),
            daily_posts=80,
            avg_comment_length=70,
            cache_hit_rate=0.5,
        ),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=route,
        search_posts=[
            {"subreddit": "FacebookAds"},
            {"subreddit": "FacebookAds"},
            {"subreddit": "buhaydigital"},
            {"subreddit": "ecommerce"},
            {"subreddit": "stocks"},
        ],
        community_profiles=aligned_profiles + route.seed_profiles,
    )

    assert result.relax_route is False
    assert result.reasons == ()
    assert result.diagnostics["route_hits"] == 4


def test_drift_guard_keeps_strong_route_when_family_query_has_generic_noise() -> None:
    plan = OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=(),
        must_not_invent=(),
        route_query_en="feeding sleep routine",
        retrieve_queries_en=("feeding sleep routine", "feeding sleep"),
        rerank_query="我们是新手父母，夜奶和睡眠记录总断档，家人换手照护时经常漏项。",
        route_keywords=("feeding", "sleep", "routine"),
        retrieve_keywords=("feeding", "sleep", "routine"),
    )
    route = OpenTopicRoute(
        warzone="Family_Parenting",
        confidence=1.0,
        reasons=("夜奶", "新手父母", "睡眠"),
        seed_profiles=(
            CommunityProfile(
                name="r/NewParents",
                categories=("seed", "warzone:Family_Parenting"),
                description_keywords=("new parent", "baby", "feeding", "sleep"),
                daily_posts=80,
                avg_comment_length=72,
                cache_hit_rate=0.55,
            ),
            CommunityProfile(
                name="r/beyondthebump",
                categories=("seed", "warzone:Family_Parenting"),
                description_keywords=("newborn", "sleep", "routine", "baby"),
                daily_posts=80,
                avg_comment_length=72,
                cache_hit_rate=0.55,
            ),
        ),
        allowed_names=frozenset({"r/newparents", "r/beyondthebump"}),
        margin=1.0,
        candidate_warzones=("Family_Parenting",),
    )

    result = evaluate_open_question_drift_guard(
        query_plan=plan,
        open_topic_route=route,
        search_posts=
        [{"subreddit": "NewParents"}] * 4
        + [{"subreddit": "beyondthebump"}] * 2
        + [{"subreddit": "BestofRedditorUpdates"}] * 20
        + [{"subreddit": "cats"}] * 12
        + [{"subreddit": "AITAH"}] * 9,
        community_profiles=route.seed_profiles,
    )

    assert result.relax_route is False
    assert result.reasons == ()
    assert result.diagnostics["route_hits"] == 6
    assert result.diagnostics["route_share"] == 0.128
