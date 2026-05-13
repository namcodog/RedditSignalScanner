from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from typing import Mapping


@dataclass(frozen=True)
class BrandRegistryRow:
    brand_key: str
    canonical_name: str
    review_status: str
    source_lifecycle: str
    domains: tuple[str, ...]
    interest_tags: tuple[str, ...]
    aliases: tuple[str, ...]
    risk_flags: tuple[str, ...]
    source_payload: Mapping[str, object]


@dataclass(frozen=True)
class BrandMentionRow:
    mention_key: str
    brand_key: str
    source: str
    source_ref: str
    community: str | None
    source_field: str | None
    source_text: str
    observed_at: str | None
    permalink: str | None
    evidence_payload: Mapping[str, object]


@dataclass(frozen=True)
class BrandRegistryPlan:
    registry_rows: tuple[BrandRegistryRow, ...]
    mention_rows: tuple[BrandMentionRow, ...]
    summary: Mapping[str, int]


def build_brand_registry_plan(
    *,
    strict_payload: Mapping[str, object],
    quality_payload: Mapping[str, object],
    digest_payload: Mapping[str, object],
) -> BrandRegistryPlan:
    quality_by_key = {
        _normalize_brand_key(_text(item.get("canonical_name"))): item
        for item in _items(quality_payload)
        if _text(item.get("review_status")) != "rejected"
    }
    rejected_quality_keys = {
        _normalize_brand_key(_text(item.get("canonical_name")))
        for item in _items(quality_payload)
        if _text(item.get("review_status")) == "rejected"
    }

    registry_rows: dict[str, BrandRegistryRow] = {}
    for item in _items(strict_payload):
        name = _text(item.get("canonical_name"))
        key = _normalize_brand_key(name)
        if not name:
            continue
        quality = quality_by_key.get(key, {})
        registry_rows[key] = BrandRegistryRow(
            brand_key=key,
            canonical_name=name,
            review_status=_status_from_strict_priority(
                _text(item.get("strict_priority"))
            ),
            source_lifecycle="user_vetted_archive",
            domains=_split_values(item.get("domains")),
            interest_tags=_split_values(quality.get("interest_tags")),
            aliases=(),
            risk_flags=_split_values(item.get("strict_flags")),
            source_payload={"strict_audit": dict(item)},
        )

    for item in quality_by_key.values():
        name = _text(item.get("canonical_name"))
        key = _normalize_brand_key(name)
        if not name:
            continue
        current = registry_rows.get(key)
        status = _text(item.get("review_status")) or "candidate"
        tags = _split_values(item.get("interest_tags"))
        if current is None:
            registry_rows[key] = BrandRegistryRow(
                brand_key=key,
                canonical_name=name,
                review_status=status,
                source_lifecycle=_text(item.get("source_lifecycle"))
                or "hotpost_quality_review",
                domains=(),
                interest_tags=tags,
                aliases=(),
                risk_flags=_split_values(item.get("noise_flags")),
                source_payload={"quality_review": dict(item)},
            )
            continue
        registry_rows[key] = replace(
            current,
            review_status="verified" if status == "verified" else current.review_status,
            interest_tags=_merge(current.interest_tags, tags),
            source_payload={**current.source_payload, "quality_review": dict(item)},
        )

    mention_rows = _build_mentions(digest_payload, registry_rows, rejected_quality_keys)
    return BrandRegistryPlan(
        registry_rows=tuple(
            sorted(registry_rows.values(), key=lambda row: row.brand_key)
        ),
        mention_rows=mention_rows,
        summary={
            "registry_rows": len(registry_rows),
            "mention_rows": len(mention_rows),
            "strict_rows": len(_items(strict_payload)),
            "quality_rows": len(_items(quality_payload)),
            "rejected_quality_rows": len(rejected_quality_keys),
        },
    )


def _build_mentions(
    digest_payload: Mapping[str, object],
    registry_rows: Mapping[str, BrandRegistryRow],
    rejected_quality_keys: set[str],
) -> tuple[BrandMentionRow, ...]:
    rows: dict[str, BrandMentionRow] = {}
    for brand in _brands(digest_payload):
        key = _normalize_brand_key(_text(brand.get("canonical_name")))
        if not key or key in rejected_quality_keys or key not in registry_rows:
            continue
        for evidence in _evidence_items(brand):
            source_text = _text(evidence.get("source_text"))
            source_ref = _text(evidence.get("card_id"))
            if not source_text or not source_ref:
                continue
            mention_key = _mention_key(key, evidence)
            rows[mention_key] = BrandMentionRow(
                mention_key=mention_key,
                brand_key=key,
                source="hotpost_published_cards",
                source_ref=source_ref,
                community=_text(evidence.get("community")) or None,
                source_field=_text(evidence.get("source")) or None,
                source_text=source_text,
                observed_at=_text(evidence.get("observed_at")) or None,
                permalink=_text(evidence.get("permalink")) or None,
                evidence_payload=dict(evidence),
            )
    return tuple(
        sorted(
            rows.values(),
            key=lambda row: (row.brand_key, row.source_ref, row.mention_key),
        )
    )


def _status_from_strict_priority(value: str) -> str:
    if value.startswith("P1_"):
        return "match_guarded"
    if value.startswith("P2_"):
        return "canonical_review"
    if value.startswith("P3_"):
        return "metadata_review"
    return "accepted"


def _mention_key(brand_key: str, evidence: Mapping[str, object]) -> str:
    parts = [
        brand_key,
        _text(evidence.get("card_id")),
        _text(evidence.get("source")),
        _text(evidence.get("source_text")),
        _text(evidence.get("permalink")),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _items(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = payload.get("items")
    return (
        tuple(item for item in value if isinstance(item, dict))
        if isinstance(value, list)
        else ()
    )


def _brands(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = payload.get("brands")
    return (
        tuple(item for item in value if isinstance(item, dict))
        if isinstance(value, list)
        else ()
    )


def _evidence_items(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = payload.get("evidence")
    return (
        tuple(item for item in value if isinstance(item, dict))
        if isinstance(value, list)
        else ()
    )


def _split_values(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        parts = re.split(r"[;,]", value)
        return tuple(part.strip() for part in parts if part.strip())
    return ()


def _merge(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys([*left, *right]))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_brand_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
