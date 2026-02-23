from app.services.semantic.smart_tagger import MatchHit, determine_l1, derive_l2, derive_l3


def test_determine_l1_priority_rules() -> None:
    pain_hit = MatchHit(term="lag", meta={"layer": "Pain"}, weight=-0.5, rule_id=1)
    pain_kw_hit = MatchHit(term="fail", meta={"concept_code": "pain_keywords"}, weight=-0.6, rule_id=2)
    neg_hit = MatchHit(term="error", meta={"negative_hits": ["error"]}, weight=-0.4, rule_id=3)

    assert determine_l1([pain_kw_hit], 0.3, "text") == "Pain"  # pain_keywords 优先
    assert determine_l1([neg_hit], -0.1, "text") == "Pain"  # negative_hits + 负情感
    assert determine_l1([], -0.4, "worst slow trash") == "Pain"  # 兜底触发词
    assert determine_l1([], 0.5, "great") == "User Need"
    assert determine_l1([], -0.2, "meh") == "Solution"


def test_derive_layers_from_meta_and_subreddit() -> None:
    hit = MatchHit(term="shopify", meta={"l2_business": "r/shopify", "layer": "L2"}, weight=0.4, rule_id=2)
    assert derive_l2([hit], "r/backup") == "r/shopify"
    assert derive_l3([hit]) == "L2"

    assert derive_l2([], "r/fallback") == "r/fallback"
