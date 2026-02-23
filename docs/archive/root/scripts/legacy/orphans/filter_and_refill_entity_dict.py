#!/usr/bin/env python3
from __future__ import annotations

"""
Filter generic terms from entity dict and refill with long-tail candidates.

Inputs:
  --dict CSV (canonical,category)
  --candidates CSV (canonical,category,layer,freq,score)
  --blacklist TXT (one term per line)
  --output CSV
  --total N (default 100)

Strategy:
  1) Remove any dict term whose lowercase is in blacklist.
  2) Refill until total terms reached, preferring (pain_points > features > brands)
     and lowest candidate freq first. Avoid duplicates.
"""

import argparse
import csv
from pathlib import Path
from typing import List, Tuple


def _load_dict(path: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            t = (row.get("canonical") or "").strip()
            c = (row.get("category") or "features").strip()
            if t:
                out.append((t, c))
    return out


def _load_candidates(path: Path) -> List[Tuple[str, str, int, float]]:
    out: List[Tuple[str, str, int, float]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            t = (row.get("canonical") or "").strip()
            c = (row.get("category") or "features").strip()
            try:
                freq = int(float(row.get("freq") or 0))
            except Exception:
                freq = 0
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            if t:
                out.append((t, c, freq, score))
    return out


def _load_blacklist(path: Path) -> set[str]:
    bl: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip().lower()
            if s:
                bl.add(s)
    return bl


def _write_dict(rows: List[Tuple[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "category"])
        w.writeheader()
        for term, cat in rows:
            w.writerow({"canonical": term, "category": cat})


def main() -> int:
    ap = argparse.ArgumentParser(description="Filter and refill entity dict using candidates")
    ap.add_argument("--dict", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--blacklist", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--min-pains", type=int, default=42)
    ap.add_argument("--max-brands", type=int, default=30)
    ap.add_argument("--brands-base", type=Path, required=False)
    ap.add_argument("--lock-pains", action="store_true")
    args = ap.parse_args()

    rows = _load_dict(args.dict)
    cands = _load_candidates(args.candidates)
    bl = _load_blacklist(args.blacklist)

    present = {t.lower() for t, _ in rows}
    filtered = [(t, c) for (t, c) in rows if t.lower() not in bl]
    present = {t.lower() for t, _ in filtered}
    # enforce brand cap by dropping surplus brands first
    brands = [(t, c) for (t, c) in filtered if c == "brands"]
    if len(brands) > args.max_brands:
        # drop least informative brands (lexicographic fallback)
        drop_n = len(brands) - args.max_brands
        to_drop = set(t.lower() for t, _ in brands[-drop_n:])
        filtered = [(t, c) for (t, c) in filtered if t.lower() not in to_drop]
        present = {t.lower() for t, _ in filtered}

    # lock existing pain points if requested (do nothing beyond avoiding removal)
    if args.lock_pains:
        pass

    # rank by category then frequency (pain points: high→low to boost coverage;
    # features/brands: low→高 to diversify)
    pains = sorted([c for c in cands if c[1] == "pain_points"], key=lambda x: (-x[2], -x[3]))
    feats = sorted([c for c in cands if c[1] == "features"], key=lambda x: (-x[2], -x[3]))
    brands = sorted([c for c in cands if c[1] == "brands"], key=lambda x: (-x[2], -x[3]))

    def _count(cat: str) -> int:
        return sum(1 for _t, c in filtered if c == cat)

    # strong-include brands base first (up to max-brands)
    if args.brands_base and args.brands_base.exists():
        base_rows = _load_dict(args.brands_base)
        for t, c in base_rows:
            if c != "brands":
                continue
            if t.lower() in bl:
                continue
            if t.lower() in present:
                continue
            if _count("brands") >= args.max_brands:
                break
            filtered.append((t, c))
            present.add(t.lower())

    # first satisfy min pains
    for t, c, _freq, _sc in pains:
        if len(filtered) >= args.total:
            break
        if _count("pain_points") >= args.min_pains:
            break
        if t.lower() in present or t.lower() in bl:
            continue
        filtered.append((t, c))
        present.add(t.lower())

    # then fill remaining slots with features > brands
    for t, c, _freq, _sc in feats + brands:
        if len(filtered) >= args.total:
            break
        if t.lower() in present or t.lower() in bl:
            continue
        if c == "brands" and _count("brands") >= args.max_brands:
            continue
        filtered.append((t, c))
        present.add(t.lower())

    _write_dict(filtered[: args.total], args.output)
    print(f"✅ filtered+refilled dict → {args.output} (size={len(filtered[: args.total])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
