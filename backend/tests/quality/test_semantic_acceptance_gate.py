from __future__ import annotations

import json
from pathlib import Path

from scripts.semantic_acceptance_gate import Thresholds, evaluate_gate


def test_gate_passes_with_defaults(tmp_path: Path) -> None:
    metrics = {
        "entity_coverage": {
            "overall": 0.72,
            "brands": 0.62,
            "features": 0.55,
            "pain_points": 0.51,
            "top10_unique_share": 0.70,
        },
        "layer_coverage": [
            {"layer": "L1", "coverage": 0.86},
            {"layer": "L2", "coverage": 0.82},
            {"layer": "L3", "coverage": 0.78},
            {"layer": "L4", "coverage": 0.72},
        ],
    }
    th = Thresholds(
        overall_coverage_min=0.70,
        brands_coverage_min=0.60,
        features_coverage_min=0.50,
        pain_points_coverage_min=0.50,
        layer_coverage_min={"L1": 0.85, "L2": 0.80, "L3": 0.75, "L4": 0.70},
        top10_unique_share_min=0.60,
        top10_unique_share_max=0.90,
        entity_dict_min_terms=100,
    )
    reasons = evaluate_gate(metrics, th, entity_terms=120)
    assert reasons == []


def test_gate_fails_and_lists_reasons() -> None:
    metrics = {
        "entity_coverage": {
            "overall": 0.50,
            "brands": 0.40,
            "features": 0.40,
            "pain_points": 0.40,
            "top10_unique_share": 0.95,
        },
        "layer_coverage": [
            {"layer": "L1", "coverage": 0.70},
            {"layer": "L2", "coverage": 0.70},
            {"layer": "L3", "coverage": 0.70},
            {"layer": "L4", "coverage": 0.60},
        ],
    }
    th = Thresholds(
        overall_coverage_min=0.70,
        brands_coverage_min=0.60,
        features_coverage_min=0.50,
        pain_points_coverage_min=0.50,
        layer_coverage_min={"L1": 0.85, "L2": 0.80, "L3": 0.75, "L4": 0.70},
        top10_unique_share_min=0.60,
        top10_unique_share_max=0.90,
        entity_dict_min_terms=100,
    )
    reasons = evaluate_gate(metrics, th, entity_terms=80)
    # Order doesn't matter; convert to set
    expected = {
        "overall_coverage<0.7",
        "brands<0.6",
        "features<0.5",
        "pain_points<0.5",
        "top10_unique_share∉[0.6,0.9]",
        "L1<0.85",
        "L2<0.8",
        "L3<0.75",
        "L4<0.7",
        "entity_terms<100",
    }
    assert set(reasons) == expected
