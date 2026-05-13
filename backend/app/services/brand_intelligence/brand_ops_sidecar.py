from __future__ import annotations

from typing import Iterable, Mapping, cast


def build_brand_ops_sidecar(
    *,
    report_date: str,
    digest_payload: Mapping[str, object],
    quality_payload: Mapping[str, object],
    registry_write_payload: Mapping[str, object] | None,
    known_brand_keys: frozenset[str],
    system_evidence_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    digest_summary = _mapping(digest_payload.get("summary"))
    quality_summary = _mapping(quality_payload.get("summary"))
    quality_items = _items(quality_payload.get("items"))
    clean_items = [
        item for item in quality_items if _text(item.get("review_status")) != "rejected"
    ]
    new_items = [
        item
        for item in clean_items
        if _brand_key(_text(item.get("canonical_name"))) not in known_brand_keys
    ]
    semantic_queue = [
        _semantic_queue_item(item)
        for item in clean_items
        if _is_semantic_queue_ready(item)
    ]

    return {
        "phase": "brand-intelligence-r15-3-daily-ops-sidecar",
        "report_date": report_date,
        "blocks_publish": False,
        "runs_after": ["hotpost_release", "mini_snapshot"],
        "auto_write_semantic_lexicon": False,
        "summary": {
            "cards_scanned": _int(digest_summary.get("card_count")),
            "brands_observed": _int(digest_summary.get("brand_count")),
            "evidence_count": _int(digest_summary.get("evidence_count")),
            "verified_brands": _status_count(quality_summary, "verified"),
            "candidate_brands": _status_count(quality_summary, "candidate"),
            "rejected_brands": _status_count(quality_summary, "rejected"),
            "noise_items": _int(quality_summary.get("noise_count")),
            "new_brand_candidates": len(new_items),
            "semantic_review_queue": len(semantic_queue),
            "registry_known_brands": len(known_brand_keys),
        },
        "interest_tag_counts": _mapping(quality_summary.get("interest_tag_counts")),
        "db_write_status": _db_write_status(registry_write_payload),
        "system_evidence_summary": _system_evidence_summary(system_evidence_payload),
        "new_brand_candidates": [
            _ops_item(item) for item in _top_items(new_items, limit=30)
        ],
        "verified_brands": [
            _ops_item(item)
            for item in _top_items(_status_items(quality_items, "verified"), limit=30)
        ],
        "noise_items": [
            _ops_item(item)
            for item in _top_items(_status_items(quality_items, "rejected"), limit=30)
        ],
        "semantic_review_queue": semantic_queue,
    }


def _db_write_status(payload: Mapping[str, object] | None) -> dict[str, object]:
    if payload is None:
        return _db_status(False, False, 0, 0, 0, 0)
    summary = _mapping(payload.get("summary"))
    return _db_status(
        True,
        payload.get("db_writes") is True,
        _int(summary.get("would_insert_registry_rows")),
        _int(summary.get("would_insert_mentions")),
        _int(summary.get("inserted_registry_rows")),
        _int(summary.get("inserted_mentions")),
    )


def _system_evidence_summary(payload: Mapping[str, object] | None) -> dict[str, object]:
    if payload is None:
        return {
            "available": False,
            "brand_count": 0,
            "mention_count": 0,
            "interest_tag_count": 0,
            "community_count": 0,
        }
    summary = _mapping(payload.get("summary"))
    return {
        "available": True,
        "brand_count": _int(summary.get("brand_count")),
        "mention_count": _int(summary.get("mention_count")),
        "interest_tag_count": _int(summary.get("interest_tag_count")),
        "community_count": _int(summary.get("community_count")),
    }


def _semantic_queue_item(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "canonical_name": _text(item.get("canonical_name")),
        "review_action": "review_for_semantic_lexicon",
        "auto_apply": False,
        "mention_count": _int(item.get("mention_count")),
        "community_count": _int(item.get("community_count")),
        "interest_tags": _strings(item.get("interest_tags")),
    }


def _ops_item(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "canonical_name": _text(item.get("canonical_name")),
        "review_status": _text(item.get("review_status")),
        "mention_count": _int(item.get("mention_count")),
        "community_count": _int(item.get("community_count")),
        "interest_tags": _strings(item.get("interest_tags")),
        "noise_flags": _strings(item.get("noise_flags")),
    }


def _db_status(
    available: bool,
    writes: bool,
    would_brands: int,
    would_mentions: int,
    brands: int,
    mentions: int,
) -> dict[str, object]:
    return {
        "available": available,
        "db_writes": writes,
        "would_insert_registry_rows": would_brands,
        "would_insert_mentions": would_mentions,
        "inserted_registry_rows": brands,
        "inserted_mentions": mentions,
    }


def _is_semantic_queue_ready(item: Mapping[str, object]) -> bool:
    return _text(item.get("review_status")) == "verified" and not _strings(
        item.get("noise_flags")
    )


def _status_items(
    items: Iterable[Mapping[str, object]], status: str
) -> list[Mapping[str, object]]:
    return [item for item in items if _text(item.get("review_status")) == status]


def _top_items(
    items: Iterable[Mapping[str, object]], *, limit: int
) -> list[Mapping[str, object]]:
    return sorted(
        items,
        key=lambda item: (
            -_int(item.get("mention_count")),
            _text(item.get("canonical_name")).lower(),
        ),
    )[:limit]


def _status_count(summary: Mapping[str, object], status: str) -> int:
    return _int(_mapping(summary.get("status_counts")).get(status))


def _items(value: object) -> list[Mapping[str, object]]:
    return (
        [cast(Mapping[str, object], item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, dict) else {}


def _strings(value: object) -> list[str]:
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int(value: object) -> int:
    return int(value) if isinstance(value, int | str) and str(value).isdigit() else 0


def _brand_key(value: str) -> str:
    return " ".join(value.strip().lower().split())
