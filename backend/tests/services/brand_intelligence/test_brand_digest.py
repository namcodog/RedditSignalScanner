from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from app.services.brand_intelligence.brand_digest import (
    build_brand_digest,
    render_brand_digest_markdown,
    write_brand_digest_outputs,
)
from app.services.semantic.unified_lexicon import UnifiedLexicon

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "brand_digest.py"
)


def _lexicon() -> UnifiedLexicon:
    return UnifiedLexicon.from_terms(
        [
            {
                "canonical": "OpenAI",
                "category": "brands",
                "aliases": ["ChatGPT"],
            },
            {
                "canonical": "Anthropic",
                "category": "brands",
                "aliases": ["Claude"],
            },
            {
                "canonical": "Shopify",
                "category": "brands",
                "aliases": ["Shop Pay"],
            },
        ]
    )


def test_digest_extracts_known_brand_evidence_from_published_cards() -> None:
    report = build_brand_digest(
        [
            {
                "card_id": "card-1",
                "title": "ChatGPT teams compare Claude and Shopify workflows",
                "summary_line": "OpenAI users are moving billing tests into Shop Pay.",
                "top_community": "r/OpenAI",
                "published_at": "2026-05-12T01:00:00Z",
                "quotes": [
                    {
                        "text": "ChatGPT saved our Shopify migration.",
                        "community": "r/ecommerce",
                        "permalink": "https://reddit.com/r/ecommerce/comments/x/y",
                    }
                ],
                "topic_cluster_id": "workflow-friction",
            }
        ],
        lexicon=_lexicon(),
        report_date="2026-05-12",
    )

    payload = report.to_payload()
    summary = cast(dict[str, object], payload["summary"])
    brands = cast(list[dict[str, object]], payload["brands"])
    openai = next(item for item in brands if item["canonical_name"] == "OpenAI")
    evidence = cast(list[dict[str, object]], openai["evidence"])

    assert summary["db_writes"] is False
    assert summary["source"] == "hotpost_published_cards"
    assert openai["matched_terms"] == ["ChatGPT", "OpenAI"]
    assert evidence
    assert {
        "card_id",
        "community",
        "source_text",
        "observed_at",
    }.issubset(evidence[0])


def test_digest_writes_deterministic_json_and_markdown(tmp_path: Path) -> None:
    report = build_brand_digest(
        [
            {
                "card_id": "card-2",
                "title": "Shop Pay checkout complaints keep showing up",
                "summary_line": "",
                "top_community": "r/shopify",
                "published_at": "2026-05-12T02:00:00Z",
            }
        ],
        lexicon=_lexicon(),
        report_date="2026-05-12",
    )
    json_path = tmp_path / "brand-digest.json"
    md_path = tmp_path / "brand-digest.md"

    write_brand_digest_outputs(report, json_path=json_path, md_path=md_path)

    payload = cast(dict[str, object], json.loads(json_path.read_text(encoding="utf-8")))
    summary = cast(dict[str, object], payload["summary"])
    markdown = md_path.read_text(encoding="utf-8")
    assert summary["brand_count"] == 1
    assert summary["db_writes"] is False
    assert "| Shopify | candidate | approved | 1 | 1 | r/shopify |" in markdown
    assert render_brand_digest_markdown(report) == markdown


def test_brand_digest_service_has_no_write_side_effects() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "SessionFactory" not in source
    assert "mutate_" not in source
    assert "write_cards_payload" not in source
    assert ".commit(" not in source
