from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.services.community.business_category_config import phase2_category_for

PHASE2_SOURCE = "community_pool_phase2_dev_write"


@dataclass(frozen=True, slots=True)
class PoolInsertRow:
    name: str
    tier: str
    categories: list[str]
    description_keywords: dict[str, Any]
    daily_posts: int
    avg_comment_length: int
    quality_score: float
    priority: str


@dataclass(frozen=True, slots=True)
class WritePlan:
    insert_rows: list[PoolInsertRow]
    skipped_existing: list[str]
    blocked_deleted_conflicts: list[str]

    @property
    def summary(self) -> dict[str, int]:
        return {
            "input_rows": len(self.insert_rows)
            + len(self.skipped_existing)
            + len(self.blocked_deleted_conflicts),
            "would_insert": len(self.insert_rows),
            "skipped_existing": len(self.skipped_existing),
            "blocked_deleted_conflicts": len(self.blocked_deleted_conflicts),
        }


def normalize_key(community: str) -> str:
    value = str(community or "").strip()
    if value.lower().startswith("r/"):
        value = value[2:]
    return value.lower()


def canonical_community_name(community: str) -> str:
    value = str(community or "").strip()
    if not value.lower().startswith("r/"):
        raise ValueError(f"invalid community name: {value}")
    return "r/" + value[2:].lower()


def infer_categories(row: dict[str, Any]) -> list[str]:
    key = normalize_key(str(row.get("community") or ""))
    role = str(row.get("role") or "")
    evidence = row.get("evidence") or {}
    scopes = set(evidence.get("supply_scopes") or [])
    return [phase2_category_for(key=key, role=role, scopes=scopes)]


def build_pool_insert_rows(phase1_payload: dict[str, Any]) -> list[PoolInsertRow]:
    if phase1_payload.get("phase") != "community-pool-phase1-dry-run":
        raise ValueError("input must be a community-pool Phase 1 dry-run payload")

    rows: list[PoolInsertRow] = []
    for row in phase1_payload.get("rows") or []:
        if row.get("phase1_action") != "propose_pool_addition":
            continue
        if not (row.get("write_preview") or {}).get("would_insert_pool"):
            continue

        display_name = str(row.get("community") or "").strip()
        name = canonical_community_name(display_name)

        evidence = row.get("evidence") or {}
        rows.append(
            PoolInsertRow(
                name=name,
                tier="seed",
                categories=infer_categories(row),
                description_keywords={
                    "source": PHASE2_SOURCE,
                    "display_name": display_name,
                    "role": row.get("role"),
                    "source_state": row.get("source_state"),
                    "cap_required": bool(row.get("cap_required")),
                    "hot_floor": row.get("hot_floor") or {},
                    "hotpost_card_count": int(evidence.get("hotpost_card_count") or 0),
                    "promotion_band": evidence.get("promotion_band"),
                    "supply_scopes": evidence.get("supply_scopes") or [],
                    "example_titles": (evidence.get("example_titles") or [])[:3],
                },
                daily_posts=0,
                avg_comment_length=0,
                quality_score=0.50,
                priority="medium",
            )
        )
    return rows


def build_write_plan(
    rows: Iterable[PoolInsertRow],
    *,
    active_existing: set[str],
    deleted_existing: set[str],
) -> WritePlan:
    insert_rows: list[PoolInsertRow] = []
    skipped_existing: list[str] = []
    blocked_deleted_conflicts: list[str] = []
    for row in rows:
        if row.name in active_existing:
            skipped_existing.append(row.name)
        elif row.name in deleted_existing:
            blocked_deleted_conflicts.append(row.name)
        else:
            insert_rows.append(row)
    return WritePlan(
        insert_rows=insert_rows,
        skipped_existing=skipped_existing,
        blocked_deleted_conflicts=blocked_deleted_conflicts,
    )


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_rollback_sql(names: list[str]) -> str:
    if not names:
        return "-- No Phase 2 community_pool rows were inserted.\n"
    quoted_names = ", ".join(_sql_literal(name) for name in names)
    return (
        "-- Roll back only rows inserted by community_pool Phase 2 Dev write.\n"
        "BEGIN;\n"
        "DELETE FROM community_category_map\n"
        "WHERE community_id IN (\n"
        "  SELECT id FROM community_pool\n"
        f"  WHERE name IN ({quoted_names})\n"
        f"    AND description_keywords->>'source' = '{PHASE2_SOURCE}'\n"
        ");\n"
        "DELETE FROM community_pool\n"
        f"WHERE name IN ({quoted_names})\n"
        f"  AND description_keywords->>'source' = '{PHASE2_SOURCE}';\n"
        "COMMIT;\n"
    )
