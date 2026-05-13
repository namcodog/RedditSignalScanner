from __future__ import annotations

from pathlib import Path
from typing import cast

from app.models.brand_registry import BrandRegistry
from app.services.brand_intelligence.brand_consumer_profile import BrandConsumerProfile
from app.services.brand_intelligence.brand_registry_reader import (
    build_brand_registry_view_payload,
    render_brand_registry_view_markdown,
)

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "brand_registry_reader.py"
)


def test_registry_view_payload_is_read_only_and_consumer_safe() -> None:
    payload = build_brand_registry_view_payload(
        [
            _brand(
                "shopify",
                "Shopify",
                ["卖家店铺运营"],
                ["电商平台与卖家工具"],
                review_status="verified",
            )
        ],
        mention_counts={"shopify": 12},
        status_filter="verified",
        interest_tag_filter="卖家店铺运营",
        consumer_profile=_consumer_profile(),
    )

    summary = cast(dict[str, object], payload["summary"])
    brands = cast(list[dict[str, object]], payload["brands"])
    consumer_contract = cast(dict[str, object], payload["consumer_contract"])

    assert payload["db_writes"] is False
    assert summary["returned_brands"] == 1
    assert summary["status_filter"] == "verified"
    assert summary["interest_tag_filter"] == "卖家店铺运营"
    assert brands[0]["brand_key"] == "shopify"
    assert brands[0]["display_name"] == "Shopify"
    assert brands[0]["business_domains"] == ["电商平台与卖家工具"]
    assert brands[0]["evidence_status"] == "verified"
    assert brands[0]["display_status"] == "已验证"
    assert brands[0]["mention_count"] == 12
    assert "review_status" not in brands[0]
    assert "domains" not in brands[0]
    assert "risk_flags" not in brands[0]
    assert "source_lifecycle" not in brands[0]
    assert consumer_contract["shared_backend_source"] == "brand_registry"
    assert consumer_contract["miniapp_snapshot_fields"] is False
    assert consumer_contract["include_internal_fields"] is False


def test_registry_view_markdown_is_operator_readable() -> None:
    payload = build_brand_registry_view_payload(
        [_brand("openai", "OpenAI", ["AI工具与Agent"], ["ai"])],
        mention_counts={"openai": 3},
        status_filter=None,
        interest_tag_filter=None,
        consumer_profile=_internal_profile(),
    )

    markdown = render_brand_registry_view_markdown(payload)

    assert "# Brand Registry Read-only View" in markdown
    assert "db_writes: `false`" in markdown
    assert "| OpenAI | openai | accepted | 3 | AI工具与Agent |" in markdown


def test_registry_reader_service_has_no_write_side_effects() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert ".commit(" not in source
    assert ".add(" not in source
    assert ".delete(" not in source
    assert "insert(" not in source
    assert "update(" not in source
    assert "delete(" not in source


def _brand(
    key: str,
    name: str,
    tags: list[str],
    domains: list[str],
    *,
    review_status: str = "accepted",
) -> BrandRegistry:
    return BrandRegistry(
        brand_key=key,
        canonical_name=name,
        review_status=review_status,
        source_lifecycle="user_vetted_archive",
        domains=domains,
        interest_tags=tags,
        aliases=[],
        risk_flags=[],
        source_payload={},
        is_active=True,
    )


def _consumer_profile() -> BrandConsumerProfile:
    return BrandConsumerProfile(
        profile_id="consumer_safe",
        review_statuses=("verified",),
        include_internal_fields=False,
        field_contract_version="brand-consumer-v1",
        display_statuses={"verified": "已验证"},
    )


def _internal_profile() -> BrandConsumerProfile:
    return BrandConsumerProfile(
        profile_id="internal_registry",
        review_statuses=(),
        include_internal_fields=True,
        field_contract_version="brand-internal-v1",
        display_statuses={},
    )
