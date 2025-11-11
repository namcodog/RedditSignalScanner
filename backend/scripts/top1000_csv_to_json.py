#!/usr/bin/env python3
from __future__ import annotations

"""
Convert a CSV (or Excel via pandas) top communities baseline into
backend/data/top1000_subreddits.json compatible with the loader.

Input columns (CSV header):
  - name (with or without r/ prefix)
  - domain_label (string)
  - tags (pipe or comma separated)
  - quality_score (0..1)
  - default_weight (0..100)
  - estimated_daily_posts (int >=0)

Usage:
  python backend/scripts/top1000_csv_to_json.py input.csv --output backend/data/top1000_subreddits.json

If the input is an .xlsx file and pandas+openpyxl are installed, the first sheet will be read.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _normalise_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return n
    return n if n.lower().startswith("r/") else f"r/{n}"


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    # support pipe or comma separated
    parts = [p.strip() for p in raw.replace("|", ",").split(",")]
    return [p for p in parts if p]


def _priority_from_weight(weight: int) -> str:
    if weight >= 80:
        return "high"
    if weight >= 50:
        return "medium"
    return "low"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def _read_excel(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pandas/openpyxl not installed. Please `pip install pandas openpyxl`. ") from exc
    df = pd.read_excel(path, engine="openpyxl")
    return df.to_dict(orient="records")


def convert(input_path: Path, output_path: Path) -> int:
    ext = input_path.suffix.lower()
    rows = _read_excel(input_path) if ext in {".xlsx", ".xls"} else _read_csv(input_path)

    items: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        name = _normalise_name(str(row.get("name", "")))
        if not name:
            # skip invalid row
            continue
        domain = str(row.get("domain_label", "")).strip()
        tags = _parse_tags(str(row.get("tags", "")))
        try:
            q = float(row.get("quality_score", 0.6))
        except Exception:
            q = 0.6
        quality_score = max(0.0, min(1.0, q))
        try:
            w = int(float(row.get("default_weight", 50)))
        except Exception:
            w = 50
        default_weight = max(0, min(100, w))
        try:
            edp = int(float(row.get("estimated_daily_posts", 0)))
        except Exception:
            edp = 0
        edp = max(0, edp)

        item = {
            "name": name,
            "domain_label": domain or None,
            "tags": tags,
            "quality_score": quality_score,
            "default_weight": default_weight,
            "estimated_daily_posts": edp,
            # fields to help current loader make better defaults
            "categories": [domain] if domain else [],
            "priority": _priority_from_weight(default_weight),
            "avg_comment_length": 100,
            "description_keywords": {t: 1.0 for t in tags} if tags else {},
            "is_active": True,
        }
        items.append(item)

    payload = {"communities": items}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Wrote {len(items)} communities to {output_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Convert top communities CSV to JSON")
    p.add_argument("input", help="Input CSV or Excel path")
    p.add_argument("--output", default="backend/data/top1000_subreddits.json", help="Output JSON path")
    args = p.parse_args()
    return convert(Path(args.input), Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())

