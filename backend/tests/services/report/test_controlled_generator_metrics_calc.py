from __future__ import annotations

from backend.app.services.report.controlled_generator import build_context


def test_ps_ratio_and_competition_saturation_computed() -> None:
    analysis = {
        "insights": {
            # pains: 4, actions: 2 → P/S ~= 2.0 : 1
            "pain_points": [
                {"description": "P1", "frequency": 10},
                {"description": "P2", "frequency": 9},
                {"description": "P3", "frequency": 8},
                {"description": "P4", "frequency": 7},
            ],
            "opportunities": [
                {"problem_definition": "S1", "suggested_actions": []},
                {"problem_definition": "S2", "suggested_actions": []},
            ],
            "pain_clusters": [{"topic": "t", "samples": ["s1"]}],
            "competitor_layers_summary": [
                {"layer": "L2", "label": "平台层", "top_competitors": []},
            ],
            "channel_breakdown": [],
        },
        "sources": {"communities": ["r/A", "r/B"]},
    }

    metrics = {
        "entity_coverage": {
            "brands": 0.6,
            "top10_unique_share": 0.5,
        },
        "layer_coverage": [
            {"layer": "L2", "coverage": 0.4},
        ],
    }

    ctx, _ = build_context(analysis, {}, metrics, task_id="t")

    # P/S ratio formatted like "2.0 : 1"
    assert ": 1" in ctx.get("ps_ratio", "")

    # Competition saturation formatted like "NN/100" and within range
    sat = ctx.get("competition_saturation", "0/100").split("/")[0]
    assert sat.isdigit()
    val = int(sat)
    assert 0 <= val <= 100

