from __future__ import annotations

import re
from typing import Iterable, Mapping, cast


def build_brand_ops_sidecar(
    *,
    report_date: str,
    digest_payload: Mapping[str, object],
    quality_payload: Mapping[str, object],
    registry_write_payload: Mapping[str, object] | None,
    known_brand_keys: frozenset[str],
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


def render_brand_ops_sidecar_markdown(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    db_status = _mapping(payload.get("db_write_status"))
    lines = [
        "# Brand Intelligence Daily Sidecar",
        "",
        f"- date: `{_text(payload.get('report_date'))}`",
        f"- blocks_publish: `{_bool_text(payload.get('blocks_publish'))}`",
        f"- auto_write_semantic_lexicon: `{_bool_text(payload.get('auto_write_semantic_lexicon'))}`",
        f"- cards_scanned: `{_int(summary.get('cards_scanned'))}`",
        f"- brands_observed: `{_int(summary.get('brands_observed'))}`",
        f"- verified_brands: `{_int(summary.get('verified_brands'))}`",
        f"- new_brand_candidates: `{_int(summary.get('new_brand_candidates'))}`",
        f"- noise_items: `{_int(summary.get('noise_items'))}`",
        f"- db_writes: `{_bool_text(db_status.get('db_writes'))}`",
        "",
        "## Daily Operator Checklist",
        "",
        "- 记录新增品牌候选和最高证据。",
        "- 记录 verified 品牌和对应兴趣标签。",
        "- 记录 rejected/noise 样本，不进入品牌池。",
        "- 记录 DB 写入状态；默认只读或 dry-run。",
        "",
        "## New Brand Candidates",
        "",
        *_brand_table(payload.get("new_brand_candidates")),
        "",
        "## Verified Brands",
        "",
        *_brand_table(payload.get("verified_brands")),
        "",
        "## Noise Items",
        "",
        *_brand_table(payload.get("noise_items")),
        "",
        "## Semantic Review Queue",
        "",
        *_queue_table(payload.get("semantic_review_queue")),
    ]
    return "\n".join(lines).rstrip() + "\n"


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


def _brand_table(value: object) -> list[str]:
    rows = (
        [_mapping(item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )
    if not rows:
        return ["- none"]
    lines = [
        "| Brand | Status | Mentions | Communities | Tags |",
        "|---|---:|---:|---:|---|",
    ]
    lines.extend(
        f"| {_cell(_text(row.get('canonical_name')))} | {_cell(_text(row.get('review_status')))} | {_int(row.get('mention_count'))} | {_int(row.get('community_count'))} | {_cell(', '.join(_strings(row.get('interest_tags'))))} |"
        for row in rows
    )
    return lines


def _queue_table(value: object) -> list[str]:
    rows = (
        [_mapping(item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )
    if not rows:
        return ["- none"]
    lines = ["| Brand | Action | Auto Apply | Tags |", "|---|---|---:|---|"]
    lines.extend(
        f"| {_cell(_text(row.get('canonical_name')))} | {_cell(_text(row.get('review_action')))} | `{_bool_text(row.get('auto_apply'))}` | {_cell(', '.join(_strings(row.get('interest_tags'))))} |"
        for row in rows
    )
    return lines


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
    return re.sub(r"\s+", " ", value.strip().lower())


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
