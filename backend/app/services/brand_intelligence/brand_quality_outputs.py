from __future__ import annotations

import json
from pathlib import Path

from app.services.brand_intelligence.brand_quality_models import BrandQualityReport


def render_brand_quality_review_markdown(report: BrandQualityReport) -> str:
    summary = report.summary
    lines = [
        "# Brand Quality Review",
        "",
        f"- date: `{summary['report_date']}`",
        f"- db_writes: `{str(summary['db_writes']).lower()}`",
        f"- cards_scanned: `{summary['card_count']}`",
        f"- brands: `{summary['brand_count']}`",
        f"- noise_items: `{summary['noise_count']}`",
        "",
        "## Status Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in _mapping(summary.get("status_counts")).items():
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## Interest Tag Summary", "", "| Tag | Brands |", "|---|---:|"])
    for tag, count in _mapping(summary.get("interest_tag_counts")).items():
        lines.append(f"| {_cell(tag)} | {count} |")
    lines.extend(["", "## Review Items", "", _review_header()])
    for item in report.items:
        lines.append(_review_row(item.to_payload()))
    lines.extend(["", "## Noise Audit", "", _noise_header()])
    for item in report.noise_items:
        lines.append(_noise_row(item.to_payload()))
    return "\n".join(lines) + "\n"


def write_brand_quality_review_outputs(
    report: BrandQualityReport,
    *,
    json_path: Path,
    md_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report.to_payload(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_brand_quality_review_markdown(report), encoding="utf-8")


def _review_header() -> str:
    return "| Brand | Status | Source | Mentions | Communities | Tags | Reason |\n|---|---:|---:|---:|---:|---|---|"


def _noise_header() -> str:
    return "| Brand | Status | Flags | Mentions | Communities | Reason |\n|---|---:|---|---:|---:|---|"


def _review_row(item: dict[str, object]) -> str:
    return (
        "| "
        + " | ".join(
            [
                _cell(str(item["canonical_name"])),
                str(item["review_status"]),
                str(item["source_lifecycle"]),
                str(item["mention_count"]),
                str(item["community_count"]),
                _cell(", ".join(_strings(item.get("interest_tags")))),
                _cell(str(item["reason"])),
            ]
        )
        + " |"
    )


def _noise_row(item: dict[str, object]) -> str:
    return (
        "| "
        + " | ".join(
            [
                _cell(str(item["canonical_name"])),
                str(item["review_status"]),
                _cell(", ".join(_strings(item.get("noise_flags")))),
                str(item["mention_count"]),
                str(item["community_count"]),
                _cell(str(item["reason"])),
            ]
        )
        + " |"
    )


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
