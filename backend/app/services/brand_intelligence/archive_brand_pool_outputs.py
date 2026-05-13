from __future__ import annotations

import csv
import json
from pathlib import Path

from app.services.brand_intelligence.archive_brand_pool_review import (
    ArchiveBrandPoolItem,
    ArchiveBrandPoolReport,
)


def render_archive_brand_pool_markdown(report: ArchiveBrandPoolReport) -> str:
    summary = report.summary
    lines = [
        "# Archive Brand Pool Preaudit",
        "",
        f"- source: `{summary['source']}`",
        f"- db_writes: `{str(summary['db_writes']).lower()}`",
        f"- raw_rows: `{summary['raw_rows']}`",
        f"- brand_count: `{summary['brand_count']}`",
        f"- duplicate_rows: `{summary['duplicate_rows']}`",
        "",
        "## Status Summary",
        "",
        "| Status | Brands |",
        "|---|---:|",
    ]
    for status, count in _mapping(summary["status_counts"]).items():
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## Domain Summary", "", "| Domain | Brands |", "|---|---:|"])
    for domain, count in _mapping(summary["domain_counts"]).items():
        lines.append(f"| {_cell(domain)} | {count} |")
    lines.extend(["", "## Needs Review", "", _table_header()])
    for item in report.items:
        if item.review_status == "needs_review":
            lines.append(_table_row(item))
    lines.extend(["", "## Full Brand List", "", _table_header()])
    for item in report.items:
        lines.append(_table_row(item))
    return "\n".join(lines) + "\n"


def write_archive_brand_pool_outputs(
    report: ArchiveBrandPoolReport,
    *,
    json_path: Path,
    md_path: Path,
    csv_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report.to_payload(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_archive_brand_pool_markdown(report), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "canonical_name",
                "review_status",
                "domains",
                "flags",
                "raw_count",
            ],
        )
        writer.writeheader()
        for item in report.items:
            writer.writerow(
                {
                    "canonical_name": item.canonical_name,
                    "review_status": item.review_status,
                    "domains": "; ".join(item.domains),
                    "flags": "; ".join(item.flags),
                    "raw_count": item.raw_count,
                }
            )


def _table_header() -> str:
    return "| Brand | Status | Domains | Flags | Raw Count |\n|---|---:|---|---|---:|"


def _table_row(item: ArchiveBrandPoolItem) -> str:
    return (
        "| "
        + " | ".join(
            [
                _cell(item.canonical_name),
                item.review_status,
                _cell(", ".join(item.domains)),
                _cell(", ".join(item.flags)),
                str(item.raw_count),
            ]
        )
        + " |"
    )


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
