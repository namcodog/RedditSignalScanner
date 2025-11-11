from __future__ import annotations

"""
Export current YAML lexicon (backend/config/semantic_sets/crossborder.yml)
to a flat CSV: theme,type,term. Includes brands, features, pain_points, exclude.

Usage:
  python backend/scripts/semantic_lexicon_export.py \
    --input backend/config/semantic_sets/crossborder.yml \
    --output backend/reports/local-acceptance/semantic-lexicon-enriched.csv
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import yaml


def main() -> None:
    ap = argparse.ArgumentParser(description="Export YAML lexicon to CSV")
    ap.add_argument("--input", type=Path, default=Path("backend/config/semantic_sets/crossborder.yml"))
    ap.add_argument("--output", type=Path, default=Path("backend/reports/local-acceptance/semantic-lexicon-enriched.csv"))
    args = ap.parse_args()

    data = yaml.safe_load(args.input.read_text(encoding="utf-8")) or {}
    themes: Dict[str, Dict[str, object]] = data.get("themes", {})  # type: ignore[assignment]

    rows: List[Dict[str, str]] = []
    for theme, cfg in themes.items():
        for bucket in ("brands", "features", "pain_points", "exclude"):
            for term in (cfg.get(bucket) or []):  # type: ignore[index]
                rows.append({"theme": str(theme), "type": bucket, "term": str(term)})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["theme", "type", "term"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"✅ Exported: {args.output}")


if __name__ == "__main__":
    main()

