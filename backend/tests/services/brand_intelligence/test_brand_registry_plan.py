from __future__ import annotations

from app.services.brand_intelligence.brand_registry_plan import (
    build_brand_registry_plan,
)


def test_registry_plan_keeps_strict_audit_risks_without_deleting_brands() -> None:
    strict_payload: dict[str, object] = {
        "items": [
            {
                "canonical_name": "Clean Brand",
                "domains": "好物选品",
                "strict_flags": "",
                "strict_priority": "P0_clean_accept",
            },
            {
                "canonical_name": "Action",
                "domains": "家居生活; 好物选品",
                "strict_flags": "common_word_collision; short_token",
                "strict_priority": "P1_text_match_risk",
            },
            {
                "canonical_name": "1688.com",
                "domains": "电商平台与卖家工具",
                "strict_flags": "contains_digit; punctuation_or_url",
                "strict_priority": "P2_canonical_form_review",
            },
            {
                "canonical_name": "Archive Keep",
                "domains": "好物选品",
                "strict_flags": "",
                "strict_priority": "P0_clean_accept",
            },
        ]
    }
    quality_payload: dict[str, object] = {
        "items": [{"canonical_name": "Archive Keep", "review_status": "rejected"}]
    }
    digest_payload: dict[str, object] = {"brands": []}

    plan = build_brand_registry_plan(
        strict_payload=strict_payload,
        quality_payload=quality_payload,
        digest_payload=digest_payload,
    )

    by_name = {row.canonical_name: row for row in plan.registry_rows}
    assert set(by_name) == {"Clean Brand", "Action", "1688.com", "Archive Keep"}
    assert by_name["Clean Brand"].review_status == "accepted"
    assert by_name["Archive Keep"].review_status == "accepted"
    assert by_name["Action"].review_status == "match_guarded"
    assert by_name["1688.com"].review_status == "canonical_review"
    assert by_name["Action"].domains == ("家居生活", "好物选品")
    assert by_name["Action"].risk_flags == ("common_word_collision", "short_token")


def test_registry_plan_adds_hotpost_mentions_for_non_rejected_brands() -> None:
    strict_payload: dict[str, object] = {"items": []}
    quality_payload: dict[str, object] = {
        "items": [
            {
                "canonical_name": "Shopify",
                "review_status": "verified",
                "interest_tags": ["卖家店铺运营"],
            },
            {"canonical_name": "Random", "review_status": "rejected"},
        ]
    }
    digest_payload: dict[str, object] = {
        "brands": [
            {
                "canonical_name": "Shopify",
                "source_lifecycle": "seed",
                "evidence": [
                    {
                        "card_id": "card-1",
                        "community": "r/shopify",
                        "source": "title",
                        "source_text": "Shopify fees changed",
                        "observed_at": "2026-05-12T00:00:00Z",
                        "permalink": "https://reddit.example/card-1",
                    }
                ],
            },
            {
                "canonical_name": "Random",
                "source_lifecycle": "candidate",
                "evidence": [
                    {
                        "card_id": "card-2",
                        "community": "r/test",
                        "source": "title",
                        "source_text": "Random text",
                        "observed_at": "2026-05-12T00:00:00Z",
                    }
                ],
            },
        ]
    }

    plan = build_brand_registry_plan(
        strict_payload=strict_payload,
        quality_payload=quality_payload,
        digest_payload=digest_payload,
    )

    assert [row.canonical_name for row in plan.registry_rows] == ["Shopify"]
    assert plan.registry_rows[0].review_status == "verified"
    assert len(plan.mention_rows) == 1
    assert plan.mention_rows[0].brand_key == "shopify"
    assert plan.mention_rows[0].source_ref == "card-1"
