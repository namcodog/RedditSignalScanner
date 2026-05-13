from __future__ import annotations

from typing import cast

from app.services.brand_intelligence.brand_registry_plan import (
    BrandMentionRow,
    BrandRegistryPlan,
    BrandRegistryRow,
)
from app.services.brand_intelligence.brand_registry_writer import (
    build_registry_write_result,
)


def test_write_result_reports_new_rows_without_mutating_existing_keys() -> None:
    plan = BrandRegistryPlan(
        registry_rows=(
            _brand_row("shopify"),
            _brand_row("stripe"),
        ),
        mention_rows=(
            _mention_row("m1", "shopify"),
            _mention_row("m2", "stripe"),
        ),
        summary={},
    )

    payload = build_registry_write_result(
        plan,
        database="reddit_signal_scanner_dev",
        dry_run=True,
        existing_brand_keys={"shopify"},
        existing_mention_keys={"m1"},
        inserted_brand_keys=(),
        inserted_mention_keys=(),
    )

    summary = cast(dict[str, object], payload["summary"])
    assert payload["db_writes"] is False
    assert summary["input_registry_rows"] == 2
    assert summary["would_insert_registry_rows"] == 1
    assert summary["would_insert_mentions"] == 1
    assert payload["skipped_existing_brand_keys"] == ["shopify"]
    assert payload["skipped_existing_mention_keys"] == ["m1"]


def test_write_result_records_execute_counts() -> None:
    plan = BrandRegistryPlan(
        registry_rows=(_brand_row("shopify"),),
        mention_rows=(_mention_row("m1", "shopify"),),
        summary={},
    )

    payload = build_registry_write_result(
        plan,
        database="reddit_signal_scanner_dev",
        dry_run=False,
        existing_brand_keys=set(),
        existing_mention_keys=set(),
        inserted_brand_keys=("shopify",),
        inserted_mention_keys=("m1",),
    )

    assert payload["db_writes"] is True
    summary = cast(dict[str, object], payload["summary"])
    assert summary["inserted_registry_rows"] == 1
    assert summary["inserted_mentions"] == 1


def _brand_row(key: str) -> BrandRegistryRow:
    return BrandRegistryRow(
        brand_key=key,
        canonical_name=key.title(),
        review_status="accepted",
        source_lifecycle="user_vetted_archive",
        domains=(),
        interest_tags=(),
        aliases=(),
        risk_flags=(),
        source_payload={},
    )


def _mention_row(key: str, brand_key: str) -> BrandMentionRow:
    return BrandMentionRow(
        mention_key=key,
        brand_key=brand_key,
        source="hotpost_published_cards",
        source_ref="card-1",
        community="r/test",
        source_field="title",
        source_text="brand mentioned",
        observed_at="2026-05-12T00:00:00Z",
        permalink=None,
        evidence_payload={},
    )
