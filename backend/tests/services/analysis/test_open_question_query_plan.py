from __future__ import annotations

from app.services.analysis.open_question_query_plan import build_open_question_query_plan


def test_build_open_question_query_plan_structures_cn_commerce_query() -> None:
    description = "卖成人用品时，最卡下单成交的地方是什么？我想看看到底是支付、审核还是信任问题卡住了转化。"

    plan = build_open_question_query_plan(
        description=description,
        keywords=("checkout", "conversion", "payment", "compliance", "trust", "ecommerce"),
    )

    assert plan.intent == "open_topic"
    assert plan.rerank_query == description
    assert "checkout" in plan.route_keywords
    assert "conversion" in plan.route_keywords
    assert "payment" in plan.retrieve_keywords
    assert plan.route_query_en == "checkout conversion payment compliance"
    assert plan.retrieve_queries_en
    assert "checkout conversion payment" in plan.retrieve_queries_en
    assert plan.must_not_invent == ()


def test_build_open_question_query_plan_preserves_ascii_entities() -> None:
    plan = build_open_question_query_plan(
        description="Next.js 14 App Router 里用 MySQL 时 timeout 怎么定位？",
        keywords=("next.js", "app router", "mysql", "timeout"),
    )

    assert "Next.js" in plan.must_keep
    assert "MySQL" in plan.must_keep
    assert "timeout" in {item.lower() for item in plan.must_keep}
