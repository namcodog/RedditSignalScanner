#!/usr/bin/env python3
from __future__ import annotations

"""
Convert enhanced semantic lexicon into candidate CSV for entity dict augmentation.

Usage:
  python -u backend/scripts/enhanced_to_candidates.py \
    --base backend/config/semantic_sets/crossborder_v2.1.yml \
    --enhanced backend/config/semantic_sets/crossborder_v2.1_enhanced.yml \
    --out backend/reports/local-acceptance/crossborder_candidates_enhanced.csv

Emits a CSV with columns: canonical,category,layer,freq,score
where freq/score are placeholders (0) since we do not recompute stats here.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Set


def load_terms(path: Path) -> Dict[str, Dict[str, List[str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    out: Dict[str, Dict[str, List[str]]] = {}
    for layer, cats in layers.items():
        out[layer] = {}
        for cat, items in cats.items():
            out[layer][cat] = [str(it.get("canonical", "")).strip() for it in items if str(it.get("canonical", "")).strip()]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Enhanced lexicon to candidate CSV")
    ap.add_argument("--base", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--enhanced", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1_enhanced.yml"))
    ap.add_argument("--out", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates_enhanced.csv"))
    args = ap.parse_args()

    base = load_terms(args.base)
    enh = load_terms(args.enhanced)
    base_set: Set[str] = set()
    for cats in base.values():
        for arr in cats.values():
            for t in arr:
                base_set.add(t.lower())

    rows: List[Dict[str, str]] = []
    for layer, cats in enh.items():
        for cat, arr in cats.items():
            for t in arr:
                if t.lower() in base_set:
                    continue
                rows.append({
                    "canonical": t,
                    "category": cat,
                    "layer": layer,
                    "freq": "0",
                    "score": "0.0",
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "category", "layer", "freq", "score"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"✅ candidates from enhanced written: {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

