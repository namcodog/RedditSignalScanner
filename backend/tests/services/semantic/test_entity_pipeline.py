from __future__ import annotations

from pathlib import Path

from app.services.analysis.entity_pipeline import EntityPipeline


def test_entity_pipeline_handles_crossborder_categories(tmp_path) -> None:
    dictionary = tmp_path / "crossborder.yml"
    dictionary.write_text(
        "\n".join(
            [
                "channels:",
                "  - Amazon",
                "  - TikTok Shop",
                "logistics:",
                "  - 3PL",
                "  - DHL",
                "risks:",
                "  - compliance",
                "  - infringement",
            ]
        ),
        encoding="utf-8",
    )

    pipeline = EntityPipeline(folder=tmp_path)
    insights = {
        "pain_points": [
            {"description": "Facing compliance risk when selling on Amazon FBA."},
        ],
        "competitors": [
            {
                "name": "TikTok Shop analytics",
                "mentions": 4,
                "sentiment": "positive",
                "context_snippets": ["3PL partners improve TikTok Shop fulfilment."],
            }
        ],
        "opportunities": [
            {
                "description": "Use DHL 3PL to speed up cross-border shipping for Amazon.",
                "relevance_score": 0.8,
                "potential_users": "~120",
                "key_insights": ["Amazon FBA sellers request DHL partnerships"],
            }
        ],
        "action_items": [],
    }

    result = pipeline.summarize(insights, top_n=5)

    assert any(item["name"] == "Amazon" for item in result.get("channels", []))
    assert any(item["name"] == "3PL" for item in result.get("logistics", []))
    assert any(item["name"] == "compliance" for item in result.get("risks", []))


def test_entity_pipeline_summarize_basic() -> None:
    pipeline = EntityPipeline(folder=str(Path(__file__).resolve().parents[3] / "backend" / "config" / "entity_dictionary"))

    insights = {
        "pain_points": [
            {"description": "Users complain about notification overload when using Slack and Discord."},
        ],
        "competitors": [
            {"name": "Notion", "mentions": 3, "sentiment": "neutral"},
        ],
        "opportunities": [
            {"description": "Build summarization and automation for calendar events", "relevance_score": 0.8, "potential_users": "~200"},
        ],
        "action_items": [],
    }

    result = pipeline.summarize(insights, top_n=5)
    # Should include categories from default.yml
    assert "brands" in result and "features" in result and "pain_points" in result
    # At least one match should be present (e.g., Slack/Discord, summarization, calendar)
    names = {item["name"] for rows in result.values() for item in rows}
    assert any(name in names for name in ("Slack", "Discord", "summarization", "calendar"))
