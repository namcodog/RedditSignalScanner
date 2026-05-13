from __future__ import annotations

from typing import cast

from app.services.brand_intelligence.brand_ops_sidecar import (
    build_brand_ops_sidecar,
)
from app.services.brand_intelligence.brand_ops_sidecar_outputs import (
    render_brand_ops_sidecar_markdown,
)


def test_sidecar_reports_non_blocking_daily_ops_contract() -> None:
    payload = build_brand_ops_sidecar(
        report_date="2026-05-13",
        digest_payload={
            "summary": {
                "card_count": 25,
                "brand_count": 3,
                "evidence_count": 7,
            }
        },
        quality_payload={
            "summary": {
                "status_counts": {"verified": 1, "candidate": 1, "rejected": 1},
                "noise_count": 1,
                "interest_tag_counts": {"AI工具与Agent": 1},
            },
            "items": [
                _item("OpenAI", "verified", 4, 2),
                _item("Acme", "candidate", 2, 1),
                _item("Case", "rejected", 8, 3, noise_flags=["generic_term"]),
            ],
        },
        registry_write_payload={
            "db_writes": False,
            "summary": {
                "would_insert_registry_rows": 1,
                "would_insert_mentions": 2,
                "inserted_registry_rows": 0,
                "inserted_mentions": 0,
            },
        },
        system_evidence_payload={
            "summary": {
                "brand_count": 13,
                "mention_count": 710,
                "interest_tag_count": 9,
                "community_count": 49,
            }
        },
        known_brand_keys=frozenset({"openai"}),
    )

    summary = cast(dict[str, object], payload["summary"])
    db_status = cast(dict[str, object], payload["db_write_status"])

    assert payload["blocks_publish"] is False
    assert payload["auto_write_semantic_lexicon"] is False
    assert summary["cards_scanned"] == 25
    assert summary["verified_brands"] == 1
    assert summary["noise_items"] == 1
    assert summary["new_brand_candidates"] == 1
    assert db_status["db_writes"] is False
    assert db_status["would_insert_registry_rows"] == 1
    assert payload["system_evidence_summary"] == {
        "available": True,
        "brand_count": 13,
        "mention_count": 710,
        "interest_tag_count": 9,
        "community_count": 49,
    }


def test_sidecar_semantic_queue_only_uses_reviewed_non_noise_brands() -> None:
    payload = build_brand_ops_sidecar(
        report_date="2026-05-13",
        digest_payload={"summary": {}},
        quality_payload={
            "summary": {},
            "items": [
                _item("OpenAI", "verified", 4, 2),
                _item("Acme", "candidate", 2, 1),
                _item("Case", "rejected", 8, 3, noise_flags=["generic_term"]),
                _item(
                    "Noisy Verified",
                    "verified",
                    4,
                    2,
                    noise_flags=["person_name_shape"],
                ),
            ],
        },
        registry_write_payload=None,
        system_evidence_payload=None,
        known_brand_keys=frozenset(),
    )

    queue = cast(list[dict[str, object]], payload["semantic_review_queue"])

    assert [item["canonical_name"] for item in queue] == ["OpenAI"]
    assert queue[0]["review_action"] == "review_for_semantic_lexicon"
    assert queue[0]["auto_apply"] is False


def test_sidecar_markdown_has_operator_sections() -> None:
    payload = build_brand_ops_sidecar(
        report_date="2026-05-13",
        digest_payload={
            "summary": {"card_count": 1, "brand_count": 1, "evidence_count": 1}
        },
        quality_payload={
            "summary": {"noise_count": 0},
            "items": [_item("OpenAI", "verified", 1, 1)],
        },
        registry_write_payload=None,
        system_evidence_payload={"summary": {"brand_count": 1}},
        known_brand_keys=frozenset(),
    )

    markdown = render_brand_ops_sidecar_markdown(payload)

    assert "## Daily Operator Checklist" in markdown
    assert "## Semantic Review Queue" in markdown
    assert "auto_write_semantic_lexicon: `false`" in markdown
    assert "system_evidence_brands: `1`" in markdown


def _item(
    name: str,
    status: str,
    mentions: int,
    communities: int,
    *,
    noise_flags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "canonical_name": name,
        "review_status": status,
        "mention_count": mentions,
        "community_count": communities,
        "interest_tags": ["AI工具与Agent"],
        "noise_flags": noise_flags or [],
    }
