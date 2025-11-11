#!/usr/bin/env python3
from __future__ import annotations

"""
Sync alias review decisions from Markdown into alias_map.csv and validate by Spec 011 thresholds.

Usage:
  python -u backend/scripts/sync_alias_decisions.py \
    --md backend/reports/local-acceptance/alias_suggestions.md \
    --csv backend/reports/local-acceptance/alias_map.csv \
    --out-csv backend/reports/local-acceptance/alias_map.csv \
    --report backend/reports/local-acceptance/alias_sync_report.json

Markdown expectations:
  Sections begin with lines like: "## canonical (L2/brands)"
  Tables have columns: alias | score | jaro | cosine | freq | ctx | decision | notes

Decisions:
  - approve
  - reject
  - merge <target>  (e.g., "merge shopify app")

Spec 011 thresholds (simplified):
  - default: Jaro >= 0.85
  - L2 brands: Jaro >= 0.90
  - L4 pain_points: Jaro >= 0.80
Targets:
  - approval_rate >= 0.70, mismerge_rate <= 0.10
"""

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class MdRow:
    canonical: str
    level: str
    category: str
    alias: str
    jaro: float
    decision: str
    notes: str


HEADER_RE = re.compile(r"^##\s+(.+?)\s*\((L[1-4])/([a-z_]+)\)")


def parse_markdown(md_path: Path) -> List[MdRow]:
    rows: List[MdRow] = []
    canonical = ""
    level = ""
    category = ""
    with md_path.open("r", encoding="utf-8") as f:
        for line in f:
            m = HEADER_RE.match(line.strip())
            if m:
                canonical, level, category = m.group(1).strip(), m.group(2), m.group(3)
                continue
            if not line.strip().startswith("|"):
                continue
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 8:
                continue
            if parts[0] == "alias":
                # header row
                continue
            alias = parts[0]
            try:
                jaro = float(parts[2])
            except Exception:
                jaro = 0.0
            decision = (parts[6] or "").strip().lower()
            notes = parts[7]
            if canonical:
                rows.append(MdRow(canonical=canonical, level=level, category=category, alias=alias, jaro=jaro, decision=decision, notes=notes))
    return rows


def jaro_threshold(target_layer: str, target_category: str) -> float:
    if target_layer == "L2" and target_category == "brands":
        return 0.90
    if target_layer == "L4" and target_category == "pain_points":
        return 0.80
    return 0.85


def sync(md_rows: List[MdRow], csv_path: Path, out_csv: Path, report_path: Path) -> Dict[str, object]:
    # Build lookup: (canonical, alias) -> (decision, notes)
    lut: Dict[Tuple[str, str], Tuple[str, str, float]] = {}
    for r in md_rows:
        key = (r.canonical.lower(), r.alias.lower())
        lut[key] = (r.decision, r.notes, r.jaro)

    in_rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            in_rows.append(row)

    total = 0
    decided = 0
    approved = 0
    mismerge = 0
    updated = 0

    for row in in_rows:
        total += 1
        canonical = (row.get("canonical") or "").strip()
        alias = (row.get("alias") or "").strip()
        tgt_layer = (row.get("target_layer") or "").strip()
        tgt_cat = (row.get("target_category") or "").strip()
        try:
            jaro = float(row.get("jaro") or 0.0)
        except Exception:
            jaro = 0.0
        key = (canonical.lower(), alias.lower())
        if key in lut:
            decision, notes, md_jaro = lut[key]
            # prefer explicit decision strings: approve/reject/merge ...
            if decision:
                row["decision"] = decision
                row["notes"] = notes
                updated += 1
        # stats
        d = (row.get("decision") or "").strip().lower()
        if d:
            decided += 1
        if d.startswith("approve"):
            approved += 1
            th = jaro_threshold(tgt_layer, tgt_cat)
            if jaro < th:
                mismerge += 1

    # write out
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(in_rows[0].keys()) if in_rows else [])
        writer.writeheader()
        for r in in_rows:
            writer.writerow(r)

    approval_rate = (approved / max(1, decided)) if decided else 0.0
    mismerge_rate = (mismerge / max(1, approved)) if approved else 0.0
    summary = {
        "total": total,
        "decided": decided,
        "approved": approved,
        "approval_rate": round(approval_rate, 4),
        "mismerge": mismerge,
        "mismerge_rate": round(mismerge_rate, 4),
        "updated_rows": updated,
        "targets": {
            "approval_rate_min": 0.70,
            "mismerge_rate_max": 0.10,
        },
        "ok": (approval_rate >= 0.70 and mismerge_rate <= 0.10),
        "out_csv": str(out_csv),
    }
    if report_path:
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync alias decisions from markdown to csv and validate thresholds")
    ap.add_argument("--md", type=Path, required=True)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--report", type=Path, default=Path("backend/reports/local-acceptance/alias_sync_report.json"))
    args = ap.parse_args()

    md_rows = parse_markdown(args.md)
    sync(md_rows, args.csv, args.out_csv, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

