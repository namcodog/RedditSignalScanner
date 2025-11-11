from __future__ import annotations

import itertools

from app.services.analysis.competitor_layering import (
    assign_competitor_layers,
    build_layer_summary,
)


def _competitor(
    name: str,
    *,
    mentions: int = 10,
    sentiment: str = "positive",
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
) -> dict:
    return {
        "name": name,
        "mentions": mentions,
        "sentiment": sentiment,
        "strengths": strengths or ["用户反馈积极"],
        "weaknesses": weaknesses or ["功能覆盖有限"],
        "market_share": 10,
        "context_snippets": [],
    }


def test_assign_competitor_layers_matches_aliases() -> None:
    competitors = [
        _competitor("Notion", mentions=40),
        _competitor("Mixpanel", mentions=35),
        _competitor("Google Sheets", mentions=30),
        _competitor("Acme Toolkit", mentions=18),
    ]

    tagged = assign_competitor_layers(competitors)

    layer_map = {item["name"]: item.get("layer") for item in tagged}
    assert layer_map["Notion"] == "workspace"
    assert layer_map["Mixpanel"] == "analytics"
    assert layer_map["Google Sheets"] == "summary"
    assert layer_map["Acme Toolkit"] == "summary"  # fallback to default layer


def test_build_layer_summary_groups_and_limits_top_three() -> None:
    competitors = [
        _competitor("Notion", mentions=50),
        _competitor("ClickUp", mentions=32),
        _competitor("Linear", mentions=21),
        _competitor("Mixpanel", mentions=44, strengths=["深度指标对比全面"]),
        _competitor("Amplitude", mentions=28, strengths=["增长团队高度依赖"]),
        _competitor("Looker", mentions=11, strengths=["BI 管理轻量化"]),
        _competitor("Google Sheets", mentions=26, strengths=["上手零门槛"]),
        _competitor("Excel", mentions=19),
        _competitor("Notion AI", mentions=15),
    ]

    tagged = assign_competitor_layers(competitors)
    summary = build_layer_summary(tagged)

    assert summary, "Expected summary entries per layer"
    layers = {entry["layer"]: entry for entry in summary}

    workspace = layers["workspace"]
    assert workspace["top_competitors"][0]["name"] == "Notion"
    assert len(workspace["top_competitors"]) == 3  # limit to top 3
    assert workspace["threats"], "Workspace layer should surface a threat insight"

    analytics = layers["analytics"]
    assert {item["name"] for item in analytics["top_competitors"]} == {
        "Mixpanel",
        "Amplitude",
        "Looker",
    }

    summary_layer = layers["summary"]
    assert list(
        itertools.islice((item["name"] for item in summary_layer["top_competitors"]), 2)
    ) == ["Google Sheets", "Excel"]
