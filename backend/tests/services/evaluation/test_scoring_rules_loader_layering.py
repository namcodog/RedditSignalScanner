import json
from pathlib import Path

from app.services.analysis.scoring_rules import ScoringRulesLoader


def test_scoring_rules_loader_buckets_rules_by_layer(tmp_path: Path) -> None:
    dummy_cfg = tmp_path / "scoring_rules.yaml"
    dummy_cfg.write_text("{}", encoding="utf-8")
    loader = ScoringRulesLoader(config_path=dummy_cfg)

    rows = [
        {"id": 1, "term": "scam", "weight": -0.5, "rule_type": "keyword", "meta": {"layer": "L1"}},
        {
            "id": 2,
            "term": "shopify",
            "weight": 0.6,
            "rule_type": "keyword",
            "meta": json.dumps({"layer": "L2"}),
        },
        {"id": 3, "term": "dropshipping", "weight": 0.4, "rule_type": "keyword", "meta": None},
    ]

    loader._build_rules_from_rows(rows)

    assert loader.layer_index["L1"][0].keyword == "scam"
    assert loader.layer_index["L2"][0].keyword == "shopify"
    assert loader.layer_index["L1"][1].keyword == "dropshipping"
