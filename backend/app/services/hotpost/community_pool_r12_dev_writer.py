from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.services.community.community_pool_phase2_dev_writer import (
    PoolInsertRow,
    canonical_community_name,
    normalize_key,
)


R12_WRITE_SOURCE = "hotpost_community_pool_r12_dev_write"
R12_PREWRITE_SOURCE = "hotpost_community_pool_r12_prewrite"


def build_r12_insert_rows(prewrite_payload: Mapping[str, Any]) -> list[PoolInsertRow]:
    if prewrite_payload.get("schema_version") != "hotpost-community-pool-r12-prewrite/v1":
        raise ValueError("input must be a Hotpost community pool R12 prewrite payload")

    rows: list[PoolInsertRow] = []
    for row in _payload_rows(prewrite_payload):
        preview = _mapping(row.get("write_preview"), "row.write_preview")
        if preview.get("action") != "prepare_dev_write" or preview.get("would_insert_pool") is not True:
            continue
        pool_insert = _mapping(preview.get("pool_insert"), "row.write_preview.pool_insert")
        name = canonical_community_name(str(pool_insert.get("name") or row.get("community") or ""))
        rows.append(
            PoolInsertRow(
                name=name,
                tier=str(pool_insert.get("tier") or "seed"),
                categories=[str(item) for item in list(pool_insert.get("categories") or [])],
                description_keywords=_description_keywords(row, pool_insert),
                daily_posts=0,
                avg_comment_length=0,
                quality_score=0.50,
                priority=str(pool_insert.get("priority") or "medium"),
            )
        )
    return rows


def build_r12_existing_name_sets(name_key_rows: Iterable[tuple[object, object]]) -> tuple[set[str], set[str]]:
    active_or_reserved: set[str] = set()
    deleted: set[str] = set()
    for raw_name_key, deleted_at in name_key_rows:
        name_key = normalize_key(str(raw_name_key or ""))
        if not name_key:
            continue
        name = f"r/{name_key}"
        if deleted_at is None:
            active_or_reserved.add(name)
        else:
            deleted.add(name)
    return active_or_reserved, deleted


def render_r12_rollback_sql(names: list[str]) -> str:
    if not names:
        return "-- No R12 community_pool rows were inserted.\n"
    quoted = ", ".join(_sql_literal(name) for name in names)
    return (
        "-- Roll back only rows inserted by Hotpost community-pool R12 Dev write.\n"
        "BEGIN;\n"
        "DELETE FROM community_category_map\n"
        "WHERE community_id IN (\n"
        "  SELECT id FROM community_pool\n"
        f"  WHERE name IN ({quoted})\n"
        f"    AND description_keywords->>'source' = '{R12_WRITE_SOURCE}'\n"
        ");\n"
        "DELETE FROM community_pool\n"
        f"WHERE name IN ({quoted})\n"
        f"  AND description_keywords->>'source' = '{R12_WRITE_SOURCE}';\n"
        "COMMIT;\n"
    )


def _description_keywords(
    row: Mapping[str, Any],
    pool_insert: Mapping[str, Any],
) -> dict[str, Any]:
    raw_keywords = pool_insert.get("description_keywords")
    source_keywords = dict(_mapping(raw_keywords, "pool_insert.description_keywords")) if raw_keywords else {}
    evidence = _mapping(row.get("evidence"), "row.evidence")
    value = _mapping(row.get("value_assessment"), "row.value_assessment")
    return {
        **source_keywords,
        "source": R12_WRITE_SOURCE,
        "prewrite_source": R12_PREWRITE_SOURCE,
        "display_name": str(row.get("community") or pool_insert.get("name") or ""),
        "source_scope": str(row.get("source_scope") or ""),
        "topic_cluster": str(row.get("topic_cluster") or ""),
        "suggested_user_tags": [str(item) for item in list(row.get("suggested_user_tags") or [])],
        "label_review": str(row.get("label_review") or ""),
        "value_stage": str(value.get("stage") or ""),
        "score": _int(value.get("score")),
        "candidate_count": _int(evidence.get("candidate_count")),
        "published_count": _int(evidence.get("published_count")),
        "duplicate_count": _int(evidence.get("duplicate_count")),
        "total_evidence": _int(evidence.get("total_evidence")),
    }


def _payload_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("prewrite payload rows must be a list")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("prewrite payload rows must be objects")
    return rows


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _int(value: object) -> int:
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    return 0


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = [
    "R12_WRITE_SOURCE",
    "build_r12_existing_name_sets",
    "build_r12_insert_rows",
    "render_r12_rollback_sql",
]
