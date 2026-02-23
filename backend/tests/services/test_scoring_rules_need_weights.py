from __future__ import annotations

import yaml

from app.services.analysis.scoring_rules import ScoringRulesLoader


def test_scoring_rules_loads_need_weights(tmp_path) -> None:
    cfg_path = tmp_path / "scoring_rules.yaml"
    payload = {
        "need_weights": {
            "Efficiency": 3.3,
            "Survival": 1.1,
        },
        "dual_label_bonus": 0.25,
    }
    cfg_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    loader = ScoringRulesLoader(config_path=cfg_path)
    rules = loader.load()

    assert rules.need_weights is not None
    assert rules.need_weights.get("Efficiency") == 3.3
    assert rules.need_weights.get("Survival") == 1.1
    assert rules.dual_label_bonus == 0.25
