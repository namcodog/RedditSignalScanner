from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = PROJECT_ROOT / "backend" / "app" / "services" / "analysis"

if str(SCRIPTS_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS_ROOT))

from app.services.analysis.entity_matcher import (
    EntityMatcher,
)  # type: ignore  # pylint: disable=wrong-import-position


@pytest.fixture(scope="session")
def matcher() -> EntityMatcher:
    return EntityMatcher(
        config_path=PROJECT_ROOT / "backend" / "config" / "entity_dictionary.yaml"
    )


def test_match_text_case_insensitive(matcher: EntityMatcher) -> None:
    text = "Notion recently shipped new automation templates but remains slow for large teams."
    result = matcher.match_text(text)

    assert "brands" in result and "Notion" in result["brands"]
    assert "features" in result and {"automation", "templates"} & set(
        result["features"]
    )
    assert "pain_points" in result and "slow" in result["pain_points"]


def test_summarize_insights_counts_mentions(matcher: EntityMatcher) -> None:
    insights = {
        "pain_points": [
            {
                "description": "Notion 的实时协作在大型团队下依旧很 slow",
                "user_examples": ["Slack 里有人抱怨手动 workflow 太多", "Trello 集成不够"],
                "example_posts": [
                    {
                        "content": "Automation workflows 在 Notion 里还是很慢",
                        "community": "r/productivity",
                    },
                ],
            }
        ],
        "competitors": [
            {"name": "Slack"},
            {"name": "Trello"},
        ],
        "opportunities": [
            {
                "description": "提供更强的 automation 模板",
                "key_insights": ["团队想要 workflow 自动化"],
                "source_examples": [
                    {"content": "模板自动化和协作是关键", "community": "r/Notion"},
                ],
            }
        ],
    }

    summary = matcher.summarize(insights, top_n=5)

    assert summary["brands"][0]["name"] == "Notion"
    assert summary["brands"][0]["mentions"] >= 2  # description + example_posts
    brand_names = {item["name"] for item in summary["brands"]}
    assert brand_names >= {"Notion", "Slack", "Trello"}

    feature_names = {item["name"] for item in summary["features"]}
    assert {"automation", "workflow"}.issubset(feature_names)

    pain_names = {item["name"] for item in summary["pain_points"]}
    assert "slow" in pain_names
