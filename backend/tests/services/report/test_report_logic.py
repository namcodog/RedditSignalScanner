import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from app.services.analysis.t1_stats import T1StatsSnapshot
from scripts.generate_t1_market_report import (
    _build_facts,
    _classify_entity,
    _compute_intent_scores,
    _pick_relevant_subreddits,
    _resolve_mode,
)
from app.services.analysis.topic_profiles import TopicProfile

def test_classify_entity():
    # Platforms
    assert _classify_entity("Amazon") == "platform"
    assert _classify_entity("Shopify") == "platform"
    
    # Channels
    assert _classify_entity("YouTube") == "channel"
    assert _classify_entity("Reddit") == "channel"
    
    # Noise
    assert _classify_entity("Price") == "noise"
    assert _classify_entity("Videos") == "noise"
    
    # Brands
    assert _classify_entity("DeLonghi") == "potential_brand"
    assert _classify_entity("Breville") == "potential_brand"
    assert _classify_entity("UnknownBrand") == "potential_brand"


def test_build_facts_market_landscape():
    # 1. Mock Stats
    stats = MagicMock(spec=T1StatsSnapshot)
    stats.since_utc = "2023-01-01"
    stats.global_ps_ratio = 1.5
    stats.community_stats = []
    stats.aspect_breakdown = []
    
    # 模拟原始数据（混杂了平台、品牌、噪音）
    # Note: Production code uses getattr(obj, "brand"), so we need objects, not dicts
    stats.brand_pain_cooccurrence = [
        SimpleNamespace(brand="Amazon", mentions=100, aspects=[]),      # Platform
        SimpleNamespace(brand="DeLonghi", mentions=50, aspects=[]),     # Brand
        SimpleNamespace(brand="YouTube", mentions=30, aspects=[]),      # Channel
        SimpleNamespace(brand="Videos", mentions=20, aspects=[]),       # Noise
        SimpleNamespace(brand="Breville", mentions=40, aspects=[]),     # Brand
    ]
    
    # 2. Mock Brand Backfill (LLM 补充的品牌)
    brand_backfill = [
        {"name": "Gaggia", "mentions": 10},        # New Brand
        {"name": "DeLonghi", "mentions": 5},       # Existing Brand (should merge?) - logic sums them
    ]
    
    # 3. Call _build_facts
    # Note: We pass empty sets for clusters/tokens to focus on market_landscape
    facts_json = _build_facts(
        stats=stats,
        clusters=[],
        topic="Coffee",
        topic_tokens=set(),
        days=365,
        brand_backfill=brand_backfill
    )
    
    facts = json.loads(facts_json)
    landscape = facts["market_landscape"]
    
    # 4. Assertions
    
    # Platforms: Amazon should be here
    platforms = [p["name"] for p in landscape["platforms"]]
    assert "Amazon" in platforms
    assert "DeLonghi" not in platforms
    
    # Channels: YouTube should be here
    channels = [c["name"] for c in landscape["channels"]]
    assert "YouTube" in channels
    
    # Brands: DeLonghi, Breville, Gaggia should be here
    brands = [b["name"] for b in landscape["brands"]]
    assert "DeLonghi" in brands
    assert "Breville" in brands
    assert "Gaggia" in brands
    assert "Amazon" not in brands
    assert "Videos" not in brands  # Noise filtered out
    
    # Mentions Count Check
    # DeLonghi: 50 (stats) + 5 (backfill) = 55
    delonghi = next(b for b in landscape["brands"] if b["name"] == "DeLonghi")
    assert delonghi["mentions"] == 55


def test_compute_intent_scores_accepts_text_field():
    scorer = MagicMock()
    scorer.score.return_value = SimpleNamespace(base_score=0.75)
    sample_comments = [{"subreddit": "r/espresso", "text": "Looking for a better grinder"}]
    scores, avg = _compute_intent_scores(sample_comments, [], scorer)
    assert scores == {"espresso": 0.75}
    assert avg == 0.75


def test_pick_relevant_subreddits_normalizes_and_limits():
    relevance_map = {"r/Coffee": 10, "espresso": 8, "Coffee": 5, "": 3}
    result = _pick_relevant_subreddits(relevance_map, limit=2)
    assert result == ["r/coffee", "r/espresso"]


def _make_profile(*, mode: str) -> TopicProfile:
    return TopicProfile(
        id="demo",
        topic_name="Demo Topic",
        product_desc="Demo Desc",
        vertical="demo",
        allowed_communities=[],
        community_patterns=[],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
        mode=mode,
    )


def test_resolve_mode_prefers_explicit_value() -> None:
    profile = _make_profile(mode="operations")
    assert _resolve_mode("market_insight", profile) == "market_insight"


def test_resolve_mode_auto_uses_profile_or_default() -> None:
    profile = _make_profile(mode="operations")
    assert _resolve_mode("auto", profile) == "operations"
    assert _resolve_mode("auto", None) == "market_insight"
