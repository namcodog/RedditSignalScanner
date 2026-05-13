from __future__ import annotations

from scripts.acceptance.run_topic_profile_full_a_matrix import _validate_full_a_contract


def _payload_with_html(report_html: str) -> dict[str, object]:
    return {
        "report_html": report_html,
        "report_structured": {
            "decision_cards": [
                {"title": "卡1", "conclusion": "结论1"},
                {"title": "卡2", "conclusion": "结论2"},
                {"title": "卡3", "conclusion": "结论3"},
                {"title": "卡4", "conclusion": "结论4"},
            ],
            "market_health": {
                "competition_saturation": {"level": "low"},
                "ps_ratio": {"ratio": "1.0"},
            },
            "battlefields": [{}, {}, {}, {}],
            "pain_points": [{}, {}, {}],
            "drivers": [{}, {}, {}],
            "opportunities": [{}, {}],
        },
        "sources": {"report_tier": "A_full"},
    }


def test_validate_full_a_contract_accepts_decision_wind_vane_heading() -> None:
    payload = _payload_with_html("## 已分析赛道（Analyzed Niche）\n\n## 决策风向标\n")

    summary = _validate_full_a_contract(payload)

    assert summary["decision_cards"] == 4
