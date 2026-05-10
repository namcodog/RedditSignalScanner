from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.hotpost.problem_frame import build_hotpost_problem_frame
from app.services.hotpost.query_planner import build_hotpost_query_plan
from app.services.hotpost.query_resolver import HotpostQueryResolution


@dataclass(frozen=True)
class RantBenchmarkCase:
    name: str
    original_query: str
    search_query: str
    keywords: list[str]
    expected_family: str
    expected_primary_friction: str | None
    expected_query_parts: list[str]


CASES = [
    RantBenchmarkCase(
        name="generic_product_complaint",
        original_query="大家最常吐槽咖啡机什么？",
        search_query="coffee machine maintenance complaints",
        keywords=["coffee", "machine", "maintenance"],
        expected_family="generic_complaint_discovery",
        expected_primary_friction="trust_gap",
        expected_query_parts=["coffee machine complaints"],
    ),
    RantBenchmarkCase(
        name="platform_conversion_friction",
        original_query="为什么TikTok内容有曝光却还是卖不出去？",
        search_query="tiktok no purchase conversion",
        keywords=["tiktok", "traffic", "purchase", "conversion"],
        expected_family="platform_conversion_friction",
        expected_primary_friction="weak_buy_reason",
        expected_query_parts=["tiktok ads no sales", "tiktok traffic low conversion"],
    ),
    RantBenchmarkCase(
        name="business_pain_discovery",
        original_query="售卖成人小玩具都有什么痛点?",
        search_query="pain points selling adult sex toys",
        keywords=["adult", "sex", "toys", "selling", "pain", "points", "challenges"],
        expected_family="business_friction_discovery",
        expected_primary_friction="weak_buy_reason",
        expected_query_parts=["adult sex toys business challenges"],
    ),
    RantBenchmarkCase(
        name="business_transaction_friction",
        original_query="卖成人用品时，最容易卡成交的地方是什么？",
        search_query="selling adult products conversion friction",
        keywords=["sex", "toys", "adult", "products", "sales", "conversion", "transaction", "friction"],
        expected_family="business_friction_discovery",
        expected_primary_friction="transaction_friction",
        expected_query_parts=["sex toys adult business challenges", "sex toys no sales"],
    ),
    RantBenchmarkCase(
        name="support_breakdown",
        original_query="tiktok seller support issue",
        search_query="tiktok seller support issue",
        keywords=["tiktok", "seller", "support", "issue"],
        expected_family="support_breakdown",
        expected_primary_friction="transaction_friction",
        expected_query_parts=["tiktok support issue"],
    ),
    RantBenchmarkCase(
        name="generic_appliance_complaint",
        original_query="大家对空气炸锅最常见的抱怨是什么？",
        search_query="air fryer cleaning complaints",
        keywords=["air", "fryer", "cleaning"],
        expected_family="generic_complaint_discovery",
        expected_primary_friction="trust_gap",
        expected_query_parts=["air fryer complaints"],
    ),
]


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_rant_problem_frame_benchmark(case: RantBenchmarkCase) -> None:
    resolution = HotpostQueryResolution(
        original_query=case.original_query,
        search_query=case.search_query,
        keywords=case.keywords,
        subreddits=[],
        source="llm",
    )
    planner = build_hotpost_query_plan(mode="rant", resolution=resolution)
    frame = build_hotpost_problem_frame(mode="rant", resolution=resolution, core_terms=planner.core_terms)

    assert planner.query_family == case.expected_family
    assert frame.query_family == case.expected_family
    assert planner.primary_friction == case.expected_primary_friction
    assert frame.primary_friction == case.expected_primary_friction
    for query_part in case.expected_query_parts:
        assert query_part in planner.query_parts
