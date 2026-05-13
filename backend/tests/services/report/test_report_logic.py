import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import textwrap
from app.services.analysis.t1_stats import T1StatsSnapshot
from scripts.report.generate_t1_market_report import (
    _build_facts,
    _build_run_identifiers,
    _classify_entity,
    _comment_dedup_sort_key,
    _compute_intent_scores,
    _deterministic_topic_expansion,
    _flatten_bucketed_items,
    _load_brand_noise,
    _parse_anchor_ts_arg,
    _pick_relevant_subreddits,
    _resolve_mode,
    _select_final_pains,
    _window_start,
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


def test_load_brand_noise_reads_general_and_operations(tmp_path) -> None:
    noise_file = tmp_path / "brand_noise.yaml"
    noise_file.write_text(
        textwrap.dedent(
            """
            general:
              - Alpha
              - beta
            operations:
              - Stripe
            """
        ).strip(),
        encoding="utf-8",
    )

    market_noise = _load_brand_noise(tmp_path, mode="market_insight")
    operations_noise = _load_brand_noise(tmp_path, mode="operations")

    assert market_noise == {"alpha", "beta"}
    assert operations_noise == {"alpha", "beta", "stripe"}


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


def test_window_start_uses_fixed_anchor_timestamp() -> None:
    anchor = datetime(2026, 3, 11, 16, 10, tzinfo=timezone.utc)
    assert _window_start(anchor, 30) == datetime(2026, 2, 9, 16, 10, tzinfo=timezone.utc)


def test_parse_anchor_ts_arg_accepts_iso_string() -> None:
    anchor = _parse_anchor_ts_arg("2026-03-12T03:00:00+00:00")
    assert anchor == datetime(2026, 3, 12, 3, 0, tzinfo=timezone.utc)


def test_deterministic_topic_expansion_uses_simple_tokenization() -> None:
    tokens, excludes, vertical = _deterministic_topic_expansion("robot vacuum cleaner")
    assert tokens == {"robot", "vacuum", "cleaner"}
    assert excludes == set()
    assert vertical == "other"


def test_build_run_identifiers_are_stable_when_anchor_is_fixed() -> None:
    anchor = datetime(2026, 3, 12, 3, 0, tzinfo=timezone.utc)
    first = _build_run_identifiers(
        topic="buy it for life products",
        product_desc="long-lasting everyday products",
        mode="market_insight",
        days=365,
        anchor_ts=anchor,
        deterministic=True,
    )
    second = _build_run_identifiers(
        topic="buy it for life products",
        product_desc="long-lasting everyday products",
        mode="market_insight",
        days=365,
        anchor_ts=anchor,
        deterministic=True,
    )
    assert first == second


def test_comment_dedup_sort_key_is_stable() -> None:
    comments = [
        {"comment_id": "t1_c2", "post_id": "t3_p2", "created_at": "2026-03-01T00:00:00+00:00", "subreddit": "r/b"},
        {"comment_id": "t1_c1", "post_id": "t3_p1", "created_at": "2026-03-02T00:00:00+00:00", "subreddit": "r/a"},
        {"comment_id": "", "post_id": "t3_p0", "created_at": "2026-03-03T00:00:00+00:00", "subreddit": "r/c"},
    ]
    ordered = sorted(comments, key=_comment_dedup_sort_key)
    assert [item["post_id"] for item in ordered] == ["t3_p0", "t3_p1", "t3_p2"]


def test_flatten_bucketed_items_sorts_bucket_keys_and_bucket_items() -> None:
    bucketed = {
        "r/b": [
            {"id": "c2", "comment_score": 1},
            {"id": "c1", "comment_score": 2},
        ],
        "r/a": [
            {"id": "c3", "comment_score": 0},
        ],
    }
    flattened = _flatten_bucketed_items(
        bucketed,
        item_sort_key=lambda item: (-(item.get("comment_score") or 0), item.get("id") or ""),
    )
    assert [item["id"] for item in flattened] == ["c3", "c1", "c2"]


def test_select_final_pains_prefers_v1_when_v2_is_too_thin() -> None:
    profile = _make_profile(mode="market_insight")
    v2_pains = [{"title": "Only one V2 pain"}]
    business_signals = {
        "high_value_pains": [
            {"description": "Products last forever"},
            {"description": "Products break less often"},
            {"description": "Products are easier to repair"},
            {"description": "Products feel durable"},
            {"description": "Products stay reliable for years"},
        ]
    }
    selected = _select_final_pains(
        v2_pains,
        business_signals,
        active_profile=profile,
        topic_filter_kw={"products"},
    )
    assert len(selected) == 5
    assert selected[0]["description"] == "Products last forever"
