from __future__ import annotations

import json
from pathlib import Path

from app.services.brand_intelligence.models import BrandDigestReport


def render_brand_digest_markdown(report: BrandDigestReport) -> str:
    payload = report.to_payload()
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise ValueError("brand digest summary must be an object")
    lines = [
        "# Brand Intelligence Digest",
        "",
        f"- date: `{summary['report_date']}`",
        f"- source: `{summary['source']}`",
        f"- db_writes: `{str(summary['db_writes']).lower()}`",
        f"- cards_scanned: `{summary['card_count']}`",
        f"- brands: `{summary['brand_count']}`",
        f"- evidence: `{summary['evidence_count']}`",
        "",
        "| Brand | Status | Source | Mentions | Communities | Top Communities |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for brand in report.brands:
        communities = sorted(brand.communities, key=str.lower)[:3]
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(brand.canonical_name),
                    brand.status,
                    brand.source_lifecycle,
                    str(len(brand.evidence)),
                    str(len(brand.communities)),
                    _cell(", ".join(communities)),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_brand_digest_outputs(
    report: BrandDigestReport,
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
    md_path.write_text(render_brand_digest_markdown(report), encoding="utf-8")


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
