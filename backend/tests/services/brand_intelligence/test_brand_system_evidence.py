from __future__ import annotations

from pathlib import Path
from typing import cast

from app.services.brand_intelligence.brand_consumer_profile import (
    load_brand_consumer_profile,
)
from app.services.brand_intelligence.brand_system_evidence import (
    BrandEvidenceRow,
    build_brand_system_evidence_payload,
)
from app.services.brand_intelligence.brand_system_evidence_outputs import (
    render_brand_system_evidence_markdown,
)


SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "brand_system_evidence.py"
)


def test_system_evidence_pack_is_backend_only_and_groups_by_tag_and_community() -> None:
    assert load_brand_consumer_profile("system_evidence").exclude_risk_flags is True
    assert load_brand_consumer_profile("system_evidence").review_statuses == ("verified",)

    payload = build_brand_system_evidence_payload(
        [
            BrandEvidenceRow(
                brand_key="shopify",
                display_name="Shopify",
                evidence_status="verified",
                business_domains=("电商平台与卖家工具",),
                interest_tags=("卖家店铺运营", "广告投放"),
                mention_count=5,
                communities=("r/shopify", "r/ecommerce"),
            ),
            BrandEvidenceRow(
                brand_key="openai",
                display_name="OpenAI",
                evidence_status="verified",
                business_domains=("AI 工具",),
                interest_tags=("AI工具与Agent",),
                mention_count=7,
                communities=("r/OpenAI",),
            ),
        ],
        profile_id="system_evidence",
    )

    summary = cast(dict[str, object], payload["summary"])
    tags = cast(list[dict[str, object]], payload["interest_tag_evidence"])
    communities = cast(list[dict[str, object]], payload["community_brand_evidence"])
    contract = cast(dict[str, object], payload["system_contract"])

    assert payload["db_writes"] is False
    assert payload["frontend_display"] is False
    assert payload["miniapp_snapshot_fields"] is False
    assert summary["brand_count"] == 2
    assert summary["mention_count"] == 12
    assert contract["not_frontend_surface"] is True
    assert contract["miniapp_benefit"] == "indirect_card_quality_and_reasoning"
    assert tags[0]["interest_tag"] == "AI工具与Agent"
    assert tags[0]["mention_count"] == 7
    assert (
        cast(list[dict[str, object]], tags[0]["brands"])[0]["display_name"] == "OpenAI"
    )
    ecommerce = next(item for item in communities if item["community"] == "r/ecommerce")
    assert ecommerce["brand_count"] == 1
    assert (
        cast(list[dict[str, object]], ecommerce["brands"])[0]["evidence_status"]
        == "verified"
    )


def test_system_evidence_markdown_states_non_frontend_contract() -> None:
    payload = build_brand_system_evidence_payload(
        [
            BrandEvidenceRow(
                brand_key="etsy",
                display_name="Etsy",
                evidence_status="verified",
                business_domains=("电商平台与卖家工具",),
                interest_tags=("好物选品",),
                mention_count=3,
                communities=("r/Etsy",),
            )
        ],
        profile_id="system_evidence",
    )

    markdown = render_brand_system_evidence_markdown(payload)

    assert "# Brand System Evidence Pack" in markdown
    assert "- frontend_display: `false`" in markdown
    assert "| 好物选品 | 1 | 3 | Etsy |" in markdown


def test_system_evidence_service_has_no_write_side_effects() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert ".commit(" not in source
    assert ".add(" not in source
    assert ".delete(" not in source
    assert "insert(" not in source
    assert "update(" not in source
    assert "delete(" not in source
