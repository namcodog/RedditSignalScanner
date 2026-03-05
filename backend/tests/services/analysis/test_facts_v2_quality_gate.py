from __future__ import annotations

from app.services.facts_v2.quality import FactsV2QualityGateConfig, quality_check_facts_v2
from app.services.analysis.topic_profiles import TopicProfile


def _profile() -> TopicProfile:
    return TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="面向 Shopify 卖家的广告优化与转化率提升工具",
        vertical="Ecommerce_Business",
        allowed_communities=["r/shopify", "r/facebookads"],
        community_patterns=["shopify", "facebookads"],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS", "CPC", "conversion"],
        exclude_keywords_any=["cake", "recipe", "cook"],
    )


def test_quality_gate_flags_topic_mismatch() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 1, "comments": 1}},
        "aggregates": {
            "communities": [{"subreddit": "r/cooking", "posts": 1, "comments": 1}]
        },
        "sample_posts_db": [{"title": "Best cake recipe ever", "subreddit": "r/cooking"}],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "I love cooking and cake", "subreddit": "r/cooking"}
        ],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.8,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert result.passed is False
    assert result.tier == "X_blocked"
    assert "topic_mismatch" in result.flags


def test_quality_gate_flags_range_mismatch() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 2}},
        "aggregates": {
            "communities": [{"subreddit": "r/shopify", "posts": 10, "comments": 10}]
        },
        "sample_posts_db": [
            {"title": "Shopify ROAS low", "subreddit": "r/shopify"},
            {"title": "Shopify CPC high", "subreddit": "r/shopify"},
        ],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "Shopify ROAS low on Facebook Ads", "subreddit": "r/shopify"},
            {"quote_id": "c2", "text": "Shopify CPC high on Facebook Ads", "subreddit": "r/shopify"},
        ],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert result.passed is False
    assert result.tier == "X_blocked"
    assert "range_mismatch" in result.flags


def test_quality_gate_flags_comments_low_when_below_min_sample_comments() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 0}},
        "aggregates": {"communities": [{"subreddit": "r/facebookads", "posts": 2, "comments": 0}]},
        "sample_posts_db": [
            {"title": "Shopify ROAS low", "subreddit": "r/facebookads"},
            {"title": "Shopify CPC high", "subreddit": "r/facebookads"},
        ],
        "sample_comments_db": [],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
        min_sample_comments=1,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert "comments_low" in result.flags
    assert result.tier == "C_scouting"


def test_quality_gate_degrades_to_c_when_comments_missing_even_if_signals_complete() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 0}},
        "aggregates": {"communities": [{"subreddit": "r/facebookads", "posts": 2, "comments": 0}]},
        "sample_posts_db": [
            {"title": "Shopify ROAS low", "subreddit": "r/facebookads"},
            {"title": "Shopify CPC high", "subreddit": "r/facebookads"},
        ],
        "sample_comments_db": [],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["p1"]},
                {"title": "CPC 高", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["p2"]},
            ],
            "brand_pain": [
                {"brand": "Shopify", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["p1"]},
                {"brand": "Facebook Ads", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["p2"]},
            ],
            "solutions": [
                {"description": "Pause Facebook Ads"},
                {"description": "Fix Shopify attribution"},
            ],
        },
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        pain_min_evidence=1,
        min_good_brands=2,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        brand_min_evidence=1,
        min_solutions=2,
        range_mismatch_tolerance=0.2,
        min_sample_comments=1,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert "comments_low" in result.flags
    assert result.tier == "C_scouting"


def test_quality_gate_flags_comments_not_used_when_db_has_comments() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {
            "source_range": {"posts": 2, "comments": 0},
            "counts_db": {"posts_current": 2, "comments_total": 12, "comments_eligible": 12},
            "comments_pipeline_status": "filtered",
        },
        "aggregates": {"communities": [{"subreddit": "r/facebookads", "posts": 2, "comments": 0}]},
        "sample_posts_db": [
            {"title": "Shopify ROAS low", "subreddit": "r/facebookads"},
            {"title": "Shopify CPC high", "subreddit": "r/facebookads"},
        ],
        "sample_comments_db": [],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["c1"]},
                {"title": "CPC 高", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["c2"]},
            ],
            "brand_pain": [
                {"brand": "Shopify", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["c1", "c3", "c4"]},
                {"brand": "Facebook Ads", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["c2", "c5", "c6"]},
            ],
            "solutions": [
                {"description": "Pause Facebook Ads"},
                {"description": "Fix Shopify attribution"},
            ],
        },
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        pain_min_evidence=1,
        min_good_brands=2,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        brand_min_evidence=1,
        min_solutions=2,
        range_mismatch_tolerance=0.2,
        # No hard requirement on sample_comments for this test; we only want the explicit flag.
        min_sample_comments=0,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert "comments_not_used" in result.flags
    assert result.tier == "A_full"


def test_quality_gate_passes_when_core_signals_complete() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 2}},
        "aggregates": {
            "communities": [{"subreddit": "r/facebookads", "posts": 2, "comments": 2}]
        },
        "sample_posts_db": [
            {"title": "Shopify ROAS low", "subreddit": "r/facebookads"},
            {"title": "Shopify CPC high", "subreddit": "r/facebookads"},
        ],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "Shopify ROAS low on Facebook Ads", "subreddit": "r/facebookads"},
            {"quote_id": "c2", "text": "Shopify CPC high on Facebook Ads", "subreddit": "r/facebookads"},
        ],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["c1"]},
                {"title": "CPC 高", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["c2"]},
            ],
            "brand_pain": [
                {"brand": "Shopify", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["c1"]},
                {"brand": "Facebook Ads", "mentions": 2, "unique_authors": 2, "evidence_quote_ids": ["c2"]},
            ],
            "solutions": [
                {"description": "Pause Facebook Ads"},
                {"description": "Fix Shopify attribution"},
            ],
        },
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        pain_min_evidence=1,
        min_good_brands=2,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        brand_min_evidence=1,
        min_solutions=2,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert result.passed is True
    assert result.tier == "A_full"
    assert not result.flags


def test_quality_gate_tier_b_trimmed_when_some_pains_exist() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 2}},
        "aggregates": {"communities": [{"subreddit": "r/shopify", "posts": 2, "comments": 2}]},
        "sample_posts_db": [
            {"title": "Shopify conversion drop", "subreddit": "r/shopify"},
            {"title": "Shopify ROAS low", "subreddit": "r/shopify"},
        ],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "Shopify ROAS low on Facebook Ads", "subreddit": "r/shopify"},
            {"quote_id": "c2", "text": "Shopify CPC high on Facebook Ads", "subreddit": "r/shopify"},
        ],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 2, "unique_authors": 2}, "evidence_quote_ids": ["c1"]}
            ],
            "brand_pain": [],
            "solutions": [],
        },
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        pain_min_evidence=1,
        min_good_brands=2,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        brand_min_evidence=1,
        min_solutions=2,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert result.passed is True
    assert result.tier == "B_trimmed"
    assert "pains_low" in result.flags


def test_quality_gate_tier_c_scouting_when_no_pains_but_on_topic() -> None:
    facts_v2 = {
        "meta": {"topic": "Shopify Traffic Ads Conversion"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 2}},
        "aggregates": {"communities": [{"subreddit": "r/facebookads", "posts": 2, "comments": 2}]},
        "sample_posts_db": [
            {"title": "Shopify traffic question", "subreddit": "r/facebookads"},
            {"title": "Shopify ads attribution", "subreddit": "r/facebookads"},
        ],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "Shopify traffic is weird on Facebook Ads", "subreddit": "r/facebookads"},
            {"quote_id": "c2", "text": "Shopify conversion tracking tips", "subreddit": "r/facebookads"},
        ],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        pain_min_evidence=1,
        min_good_brands=2,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        brand_min_evidence=1,
        min_solutions=2,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=_profile(), config=cfg)
    assert result.passed is True
    assert result.tier == "C_scouting"
    assert "pains_low" in result.flags


def test_quality_gate_skips_topic_check_without_profile() -> None:
    facts_v2 = {
        "meta": {"topic": "Generic"},
        "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
        "aggregates": {"communities": [{"subreddit": "r/test", "posts": 1, "comments": 0}]},
        "sample_posts_db": [{"title": "Unrelated text", "subreddit": "r/test"}],
        "sample_comments_db": [],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.9,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(
        facts_v2,
        profile=None,
        config=cfg,
        skip_topic_check=True,
    )
    assert "topic_mismatch" not in result.flags
    assert result.tier == "A_full"


def test_quality_gate_auto_skips_topic_check_when_profile_missing_and_no_fallback_terms() -> None:
    facts_v2 = {
        "meta": {
            "topic": "全中文主题",
            "product_description": "全中文描述，没有任何英文关键字",
        },
        "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
        "aggregates": {"communities": [{"subreddit": "r/test", "posts": 1, "comments": 0}]},
        "sample_posts_db": [{"title": "Unrelated text", "subreddit": "r/test"}],
        "sample_comments_db": [],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.9,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(
        facts_v2,
        profile=None,
        config=cfg,
    )
    assert result.passed is True
    assert result.tier == "A_full"
    assert "topic_mismatch" not in result.flags
    assert bool(result.metrics.get("topic_check_skipped")) is True


def test_quality_gate_uses_profile_threshold_overrides_by_default() -> None:
    # Without overrides, defaults are quite strict (e.g. min_solutions=5).
    # Narrow-topic profiles can lower them so we can still classify tier correctly.
    profile = TopicProfile(
        id="demo",
        topic_name="Demo Topic",
        product_desc="desc",
        vertical="demo",
        allowed_communities=["r/demo"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=["Facebook Ads"],
        include_keywords_any=["ROAS"],
        exclude_keywords_any=[],
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        min_solutions=1,
    )
    facts_v2 = {
        "meta": {"topic": "Demo Topic"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 2}},
        "aggregates": {"communities": [{"subreddit": "r/demo", "posts": 2, "comments": 2}]},
        "sample_posts_db": [{"title": "Shopify ROAS", "subreddit": "r/demo"}],
        "sample_comments_db": [
            {"quote_id": "c1", "text": "Shopify ROAS low on Facebook Ads", "subreddit": "r/demo"}
        ],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 1, "unique_authors": 1}, "evidence_quote_ids": ["c1"]},
                {"title": "CPC 高", "metrics": {"mentions": 1, "unique_authors": 1}, "evidence_quote_ids": ["c1"]},
            ],
            "brand_pain": [
                {"brand": "Shopify", "mentions": 1, "unique_authors": 1, "evidence_quote_ids": ["c1", "c2", "c3"]},
                {"brand": "Facebook Ads", "mentions": 1, "unique_authors": 1, "evidence_quote_ids": ["c1", "c2", "c3"]},
            ],
            "solutions": [{"description": "Pause ads"}],
        },
    }
    result = quality_check_facts_v2(facts_v2, profile=profile)
    assert result.tier == "A_full"


def test_quality_gate_uses_profile_min_sample_comments_override() -> None:
    profile = TopicProfile(
        id="demo_comments",
        topic_name="Demo Topic",
        product_desc="desc",
        vertical="demo",
        allowed_communities=["r/demo"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS"],
        exclude_keywords_any=[],
        pain_min_mentions=1,
        pain_min_unique_authors=1,
        brand_min_mentions=1,
        brand_min_unique_authors=1,
        min_solutions=1,
        min_sample_comments=1,
    )
    facts_v2 = {
        "meta": {"topic": "Demo Topic"},
        "data_lineage": {"source_range": {"posts": 2, "comments": 0}},
        "aggregates": {"communities": [{"subreddit": "r/demo", "posts": 2, "comments": 0}]},
        "sample_posts_db": [{"title": "Shopify ROAS", "subreddit": "r/demo"}],
        "sample_comments_db": [],
        "business_signals": {
            "high_value_pains": [
                {"title": "ROAS 低", "metrics": {"mentions": 1, "unique_authors": 1}, "evidence_quote_ids": ["p1"]},
                {"title": "CPC 高", "metrics": {"mentions": 1, "unique_authors": 1}, "evidence_quote_ids": ["p2"]},
            ],
            "brand_pain": [
                {"brand": "Shopify", "mentions": 1, "unique_authors": 1, "evidence_quote_ids": ["p1"]},
                {"brand": "Facebook Ads", "mentions": 1, "unique_authors": 1, "evidence_quote_ids": ["p2"]},
            ],
            "solutions": [{"description": "Fix attribution"}],
        },
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.5,
        min_good_pains=2,
        min_good_brands=2,
        min_solutions=1,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=profile, config=cfg)
    assert "comments_low" in result.flags
    assert result.tier == "C_scouting"


def test_quality_gate_marks_coverage_capped() -> None:
    facts_v2 = {
        "meta": {"topic": "Generic"},
        "data_lineage": {
            "source_range": {"posts": 1, "comments": 0},
            "coverage": {
                "status_counts": {"DONE_CAPPED": 1},
                "coverage_months_min": 3,
                "coverage_months_avg": 3,
                "coverage_months_max": 3,
                "capped_count": 1,
            },
        },
        "aggregates": {"communities": [{"subreddit": "r/test", "posts": 1, "comments": 0}]},
        "sample_posts_db": [{"title": "Shopify ROAS low", "subreddit": "r/test"}],
        "sample_comments_db": [],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.0,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(
        facts_v2,
        profile=None,
        config=cfg,
        skip_topic_check=True,
    )
    assert result.metrics["coverage_tier"] == "capped"
    assert "coverage_capped" in result.flags


def test_quality_gate_marks_coverage_full() -> None:
    facts_v2 = {
        "meta": {"topic": "Generic"},
        "data_lineage": {
            "source_range": {"posts": 1, "comments": 0},
            "coverage": {
                "status_counts": {"DONE_12M": 1},
                "coverage_months_min": 12,
                "coverage_months_avg": 12,
                "coverage_months_max": 12,
                "capped_count": 0,
            },
        },
        "aggregates": {"communities": [{"subreddit": "r/test", "posts": 1, "comments": 0}]},
        "sample_posts_db": [{"title": "Shopify ROAS low", "subreddit": "r/test"}],
        "sample_comments_db": [],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=0.0,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(
        facts_v2,
        profile=None,
        config=cfg,
        skip_topic_check=True,
    )
    assert result.metrics["coverage_tier"] == "full"
    assert "coverage_capped" not in result.flags
    assert "coverage_partial" not in result.flags


def test_quality_gate_topic_match_uses_profile_context_keywords() -> None:
    profile = TopicProfile(
        id="demo",
        topic_name="Demo Topic",
        product_desc="desc",
        vertical="demo",
        allowed_communities=["r/demo"],
        community_patterns=[],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
        require_context_for_fetch=True,
        context_keywords_any=["pixel"],
    )
    facts_v2 = {
        "meta": {"topic": "Demo Topic"},
        "data_lineage": {"source_range": {"posts": 1, "comments": 1}},
        "aggregates": {"communities": [{"subreddit": "r/demo", "posts": 1, "comments": 1}]},
        "sample_posts_db": [],
        "sample_comments_db": [{"quote_id": "c1", "text": "pixel not firing", "subreddit": "r/demo"}],
        "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
    }
    cfg = FactsV2QualityGateConfig(
        min_on_topic_ratio=1.0,
        min_good_pains=0,
        min_good_brands=0,
        min_solutions=0,
        range_mismatch_tolerance=0.2,
    )
    result = quality_check_facts_v2(facts_v2, profile=profile, config=cfg)
    assert result.passed is True
    assert "topic_mismatch" not in result.flags
