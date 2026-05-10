from __future__ import annotations

from app.services.hotpost.preview_projection import apply_hotpost_preview_projection


def test_apply_hotpost_preview_projection_prefers_quotes_that_support_primary_signal() -> None:
    payload = {
        "unmet_needs": [
            {
                "need": "Need better chargeback response automation",
                "opportunity_insight": "Teams keep losing chargeback response cases after submitting evidence.",
                "user_voice": "We keep losing disputes because the evidence packet is too manual.",
                "current_workarounds": [{"name": "manual review"}],
            }
        ],
        "market_opportunity": {"target_user": "高拒付风险的中小电商卖家"},
        "top_quotes": [
            {"quote": "This payroll checklist saved my HR team.", "score": 98, "url": "https://reddit.com/x"},
            {
                "quote": "We keep losing chargeback response cases because the evidence packet is too manual.",
                "score": 12,
                "url": "https://reddit.com/y",
            },
        ],
    }

    projected = apply_hotpost_preview_projection(mode="opportunity", state="preview", payload=payload)

    quotes = projected["top_quotes"]
    assert len(quotes) == 1
    assert "chargeback response cases" in quotes[0]["quote"]


def test_apply_hotpost_preview_projection_rewrites_preview_opportunity_recommendation() -> None:
    payload = {
        "unmet_needs": [
            {
                "need": "Need better chargeback response automation",
                "opportunity_insight": "Teams keep losing chargeback response cases after submitting evidence.",
                "user_voice": "We keep losing disputes because the evidence packet is too manual and takes hours every week.",
                "current_workarounds": [{"name": "manual review"}],
            }
        ],
        "market_opportunity": {
            "target_user": "高拒付风险的中小电商卖家",
            "unmet_gap": "Teams keep losing chargeback response cases after submitting evidence.",
            "recommendation": "旧建议",
        },
        "top_quotes": [],
    }

    projected = apply_hotpost_preview_projection(mode="opportunity", state="preview", payload=payload)
    recommendation = projected["market_opportunity"]["recommendation"]

    assert "高拒付风险的中小电商卖家" in recommendation
    assert "manual review" in recommendation
    assert "验证" in recommendation
    assert "chargeback response cases" in recommendation


def test_apply_hotpost_preview_projection_normalizes_target_user_with_config_rules() -> None:
    payload = {
        "unmet_needs": [
            {
                "need": "Need better chargeback response automation",
                "opportunity_insight": "Teams keep losing chargeback response cases after submitting evidence.",
                "current_workarounds": [{"name": "manual review"}],
            }
        ],
        "market_opportunity": {
            "target_user": "Shopify使用SaaS founders",
            "unmet_gap": "Teams keep losing chargeback response cases after submitting evidence.",
        },
        "top_quotes": [],
    }

    projected = apply_hotpost_preview_projection(mode="opportunity", state="preview", payload=payload)
    target_user = projected["market_opportunity"]["target_user"]

    assert target_user == "使用 Shopify 的 SaaS 创始人"
    assert "使用 Shopify 的 SaaS 创始人" in projected["market_opportunity"]["recommendation"]


def test_apply_hotpost_preview_projection_leaves_standard_payload_unchanged() -> None:
    payload = {
        "top_quotes": [{"quote": "keep this quote", "score": 1}],
        "market_opportunity": {"recommendation": "keep this recommendation"},
    }

    projected = apply_hotpost_preview_projection(mode="opportunity", state="standard", payload=payload)

    assert projected == payload


def test_apply_hotpost_preview_projection_hides_weak_rant_posts_and_keywords_on_no_hit() -> None:
    payload = {
        "pain_points": [],
        "top_posts": [{"id": "generic-post", "title": "Generic complaint"}],
        "top_rants": [{"id": "generic-post", "title": "Generic complaint"}],
        "next_steps": {"suggested_keywords": ["tiktok", "views", "sales"]},
    }

    projected = apply_hotpost_preview_projection(mode="rant", state="no_hit", payload=payload)

    assert projected["top_posts"] == []
    assert projected["top_rants"] == []
    assert projected["next_steps"]["suggested_keywords"] == []


def test_apply_hotpost_preview_projection_prefers_rant_pain_point_evidence_posts() -> None:
    payload = {
        "pain_points": [
            {
                "category": "Traffic mismatch",
                "evidence_posts": [
                    {"id": "pain-post", "title": "TikTok views are high but nobody buys"},
                ],
            }
        ],
        "top_posts": [{"id": "generic-post", "title": "Generic marketing advice"}],
    }

    projected = apply_hotpost_preview_projection(mode="rant", state="preview", payload=payload)

    assert [post["id"] for post in projected["top_posts"]] == ["pain-post"]


def test_apply_hotpost_preview_projection_falls_back_to_existing_rant_posts_when_no_pain_points() -> None:
    payload = {
        "pain_points": [],
        "top_posts": [{"id": "quote-backed-post", "title": "TikTok Shop has fallen off"}],
    }

    projected = apply_hotpost_preview_projection(mode="rant", state="preview", payload=payload)

    assert [post["id"] for post in projected["top_posts"]] == ["quote-backed-post"]
