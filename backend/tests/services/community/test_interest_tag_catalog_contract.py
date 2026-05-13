from __future__ import annotations

import json

from app.services.community.community_recommendation_preview import (
    CommunitySignal,
    build_capability_tags,
)
from app.services.community.interest_tag_catalog import DEFAULT_CATALOG_PATH, load_interest_tag_catalog


def _catalog_payload() -> dict[str, object]:
    payload = json.loads(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_user_selectable_tags_are_configured_once() -> None:
    payload = _catalog_payload()
    contract = payload["contract"]
    raw_tags = payload["tags"]
    assert isinstance(contract, dict)
    assert isinstance(raw_tags, list)

    catalog = load_interest_tag_catalog()

    assert len(catalog.tags) == contract["tag_count"] == len(raw_tags)
    assert [tag.display_name for tag in catalog.tags] == [tag["display_name"] for tag in raw_tags]
    assert len({tag.tag_id for tag in catalog.tags}) == len(catalog.tags)
    assert len({tag.display_name for tag in catalog.tags}) == len(catalog.tags)


def test_backend_mapping_refs_are_config_driven_and_complete() -> None:
    payload = _catalog_payload()
    contract = payload["contract"]
    raw_tags = payload["tags"]
    assert isinstance(contract, dict)
    assert isinstance(raw_tags, list)
    prefixes = tuple(contract["allowed_source_ref_prefixes"])

    for raw_tag in raw_tags:
        source_refs = raw_tag["source_refs"]
        match = raw_tag["match"]
        assert source_refs
        assert all(str(ref).startswith(prefixes) for ref in source_refs)
        assert match["keywords"] or match["semantic_terms"] or match["categories"]


def test_preview_tag_order_and_names_come_from_config() -> None:
    payload = _catalog_payload()
    raw_tags = payload["tags"]
    assert isinstance(raw_tags, list)
    signals = []
    for raw_tag in raw_tags:
        match = raw_tag["match"]
        keys = tuple(match["keywords"] or match["semantic_terms"] or match["categories"])
        signals.append(
            CommunitySignal(
                community=f"r/{raw_tag['id']}",
                categories=tuple(match["categories"]),
                keywords=keys[:2],
                semantic_terms=keys[:2],
                recent_posts_15d=1,
                hotpost_cards=1,
            )
        )

    tags = build_capability_tags(signals)

    assert [tag.tag_id for tag in tags] == [tag["id"] for tag in raw_tags]
    assert [tag.name for tag in tags] == [tag["display_name"] for tag in raw_tags]
    assert all(tag.user_input_required is False for tag in tags)
