#!/usr/bin/env python3
from __future__ import annotations

"""
Merge existing semantic candidates with a lightweight contributed seed CSV.

Inputs:
  --base-candidates CSV produced by extract_candidates.py
  --contrib-csv CSV with columns [canonical,category]
  --out-csv Output merged CSV with columns [canonical,category,layer,freq,score]

Notes:
  - For contrib rows, we assign heuristic defaults:
      layer: L1 for brands/features, L4 for pain_points
      freq:  50 for pain_points, 40 for features, 60 for brands
      score: 1.0
  - Deduplicates by canonical lowercase (base wins; contrib fills missing)
"""

import argparse
import csv
from pathlib import Path
from typing import Dict


def _read_base(path: Path) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = (row.get("canonical") or "").strip()
            if not t:
                continue
            key = t.lower()
            out[key] = {
                "canonical": t,
                "category": (row.get("category") or "features").strip(),
                "layer": (row.get("layer") or "").strip(),
                "freq": (row.get("freq") or "0").strip(),
                "score": (row.get("score") or "0").strip(),
            }
    return out


def _defaults_for_category(cat: str) -> tuple[str, int, float]:
    c = (cat or "features").strip()
    if c == "pain_points":
        return ("L4", 50, 1.0)
    if c == "brands":
        return ("L1", 60, 1.0)
    return ("L1", 40, 1.0)


def _read_contrib(path: Path) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader((line for line in f if not line.lstrip().startswith("#")))
        for row in reader:
            t = (row.get("canonical") or "").strip()
            if not t:
                continue
            cat = (row.get("category") or "features").strip()
            layer, freq, score = _defaults_for_category(cat)
            key = t.lower()
            out[key] = {
                "canonical": t,
                "category": cat,
                "layer": layer,
                "freq": str(freq),
                "score": str(score),
            }
    return out


def _write(out_map: Dict[str, Dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "category", "layer", "freq", "score"])
        w.writeheader()
        for key in sorted(out_map.keys()):
            w.writerow(out_map[key])


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge candidates with contributed seed CSV")
    ap.add_argument("--base-candidates", type=Path)
    ap.add_argument("--contrib-csv", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    args = ap.parse_args()

    base = _read_base(args.base_candidates) if args.base_candidates else {}
    contrib = _read_contrib(args.contrib_csv)
    merged = dict(base)
    for k, v in contrib.items():
        if k not in merged:
            merged[k] = v
    _write(merged, args.out_csv)
    print(f"✅ merged candidates → {args.out_csv} (base={len(base)}, contrib={len(contrib)}, total={len(merged)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

