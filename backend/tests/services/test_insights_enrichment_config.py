from __future__ import annotations

import yaml

from app.services.analysis import insights_enrichment as ie


def test_insights_enrichment_config_overrides(monkeypatch, tmp_path) -> None:
    cfg_path = tmp_path / "insights_enrichment.yaml"
    payload = {
        "trend_label_map": {
            "CUSTOM": "自定义趋势",
        },
        "driver_rules": [
            {"keywords": ["foo"], "driver": "Foo驱动"},
        ],
        "driver_actions": {
            "Foo驱动": ["动作1"],
        },
    }
    cfg_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("INSIGHTS_ENRICHMENT_CONFIG_PATH", str(cfg_path))
    ie._reset_insights_config_cache()

    series = [{"trend": "CUSTOM", "count": 3, "growth_rate": 0.2, "recent_velocity": 0.1}]
    res = ie.summarize_trend_series(series, degraded=False, sources=None)
    assert res["label"] == "自定义趋势"

    label = ie.derive_driver_label("foo is great")
    assert label == "Foo驱动"

    drivers = ie.build_top_drivers(
        [{"description": "foo is slow", "frequency": 2}],
        action_items=None,
        limit=1,
    )
    assert drivers[0]["actions"] == ["动作1"]
