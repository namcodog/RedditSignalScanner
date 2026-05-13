from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Protocol, cast


class _CatalogLike(Protocol):
    @property
    def summary(self) -> dict[str, object]:
        ...

    def to_payload(self) -> dict[str, object]:
        ...


def render_brand_source_catalog_markdown(catalog: _CatalogLike) -> str:
    summary = catalog.summary
    lifecycle_counts = _as_mapping(summary.get("lifecycle_counts"))
    lines = [
        "# Brand Source Catalog",
        "",
        f"- total_entries: `{summary.get('total_entries', 0)}`",
        f"- duplicate_keys: `{_count_items(summary.get('duplicate_keys'))}`",
        f"- noise_overlaps: `{_count_items(summary.get('noise_overlaps'))}`",
        "",
        "| Lifecycle | Count |",
        "|---|---:|",
    ]
    for lifecycle in ("approved", "seed", "candidate", "rejected"):
        lines.append(f"| {lifecycle} | {lifecycle_counts.get(lifecycle, 0)} |")
    return "\n".join(lines) + "\n"


def write_brand_source_catalog_outputs(
    catalog: _CatalogLike,
    *,
    json_path: Path,
    md_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(catalog.to_payload(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_brand_source_catalog_markdown(catalog), encoding="utf-8")


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast(Mapping[str, object], value)


def _count_items(value: object) -> int:
    return len(value) if isinstance(value, list) else 0
