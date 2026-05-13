from __future__ import annotations

from pathlib import Path

from app.services.community.community_recommendation_preview import (
    CommunitySignal,
    build_capability_tags,
)
from app.services.community.interest_tag_catalog import load_interest_tag_catalog


COMMUNITY_SERVICE_DIR = Path(__file__).resolve().parents[3] / "app" / "services" / "community"


def test_contract_has_no_business_seed_constant_in_service_source() -> None:
    source = (COMMUNITY_SERVICE_DIR / "community_recommendation_preview.py").read_text(encoding="utf-8")
    catalog = load_interest_tag_catalog()

    assert "CAPABILITY_SEEDS" not in source
    assert not any(tag.display_name in source for tag in catalog.tags)


def test_core_does_not_hardcode_interest_tag_ids() -> None:
    source = (COMMUNITY_SERVICE_DIR / "community_recommendation_core.py").read_text(encoding="utf-8")
    catalog = load_interest_tag_catalog()

    assert not any(tag.tag_id in source for tag in catalog.tags)


def test_source_ref_match_covers_ecommerce_platform_risk() -> None:
    source_ref = "topic_cluster:unit-economics-and-platform-risk"
    signals = [
        CommunitySignal(
            community="r/FulfillmentByAmazon",
            keywords=("fba fee increase", "amazon policy change", "platform risk"),
            semantic_terms=("fulfillment cost", "platform policy", "unit economics"),
            source_refs=(source_ref,),
            recent_posts_15d=2,
            hotpost_cards=3,
        )
    ]

    tag = next(tag for tag in build_capability_tags(signals) if source_ref in tag.source_refs)

    assert tag.community_count == 1
    assert tag.status == "ready"
