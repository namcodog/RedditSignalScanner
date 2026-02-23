#!/usr/bin/env python3
from __future__ import annotations

"""
Refine v2.1 semantic sets by deduplicating across layers and filling back
with high-quality candidates to keep total=500 while increasing uniqueness.

Inputs:
  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml
  --candidates backend/reports/local-acceptance/crossborder_candidates.csv
  --output backend/config/semantic_sets/crossborder_v2.1_refined.yml

Heuristics:
  - Keep each canonical only once across all layers according to priority:
      brands/features: L2 > L3 > L1 > L4 ; pain_points: L3 > L2 > L4 > L1
  - Replace duplicate slots with candidate phrases (prefer phrases, non-generic),
    mapping candidate category to corresponding category; if features short, fill features.
  - Generic and low-signal filters similar to entity dict.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set

PRIORITY = {
    "brands": ["L2", "L3", "L1", "L4"],
    "features": ["L2", "L3", "L1", "L4"],
    "pain_points": ["L3", "L2", "L4", "L1"],
}

GENERIC = {
    "help", "new", "time", "people", "need", "don", "does", "doing", "way",
    "best", "good", "thanks", "using", "order", "orders", "online", "page", "site",
    "www", "email", "year", "month", "day", "guys", "better", "product", "products",
    "store", "stores", "brand", "brands", "marketing", "ad", "ads", "company",
    "experience", "content", "business", "looking", "work", "really", "sell", "selling", "sales",
    "customer", "customers", "account", "website",
}

def load_lex(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))

def unique_terms(d: Dict) -> Tuple[int, int]:
    total = 0
    terms: List[str] = []
    for cats in d.get("layers", {}).values():
        for arr in cats.values():
            total += len(arr)
            terms.extend([str(x.get("canonical", "")).lower() for x in arr])
    return total, len(set(terms))

def load_candidates(path: Path) -> List[Tuple[str, str, str, int, float]]:
    out: List[Tuple[str, str, str, int, float]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get("canonical") or "").strip()
            cat = (row.get("category") or "features").strip()
            layer = (row.get("layer") or "L2").strip()
            try:
                freq = int(row.get("freq") or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            out.append((can, cat, layer, freq, score))
    # sort by score then freq
    out.sort(key=lambda x: (-x[4], -x[3]))
    return out

def is_phrase(s: str) -> bool:
    return (" " in s) or ("-" in s) or ("/" in s)

def refine_and_fill(data: Dict, cands: List[Tuple[str, str, str, int, float]]) -> Dict:
    layers = data.get("layers", {})
    out_layers: Dict[str, Dict[str, List[Dict]]] = {k: {"brands": [], "features": [], "pain_points": []} for k in ["L1", "L2", "L3", "L4"]}
    seen: Set[str] = set()
    pending_slots: List[Tuple[str, str]] = []  # (layer, category)

    # Step 1: keep uniques by category priority
    for cat, pri in PRIORITY.items():
        for lay in pri:
            for item in layers.get(lay, {}).get(cat, []):
                can = str(item.get("canonical", "")).strip()
                if not can:
                    continue
                key = can.lower()
                if key in seen:
                    # will fill later in same layer/category
                    pending_slots.append((lay, cat))
                    continue
                seen.add(key)
                out_layers[lay][cat].append({
                    "canonical": can,
                    "aliases": item.get("aliases", []),
                    "precision_tag": item.get("precision_tag", "phrase"),
                    "weight": item.get("weight", 1.0),
                    "polarity": item.get("polarity", "neutral"),
                })

    # Step 2: fill pending with candidate phrases
    def good_candidate(can: str, cat: str) -> bool:
        low = can.lower()
        if len(low) < 3:
            return False
        if low in GENERIC:
            return False
        if not is_phrase(can) and cat == "features":
            return False
        return True

    cand_idx = 0
    while pending_slots and cand_idx < len(cands):
        can, cat, lay, freq, score = cands[cand_idx]
        cand_idx += 1
        if can.lower() in seen or not good_candidate(can, cat):
            continue
        # allocate into first pending slot of same category, else any slot
        idx = next((i for i, (pl, pc) in enumerate(pending_slots) if pc == cat), None)
        if idx is None:
            idx = 0
        pl, pc = pending_slots.pop(idx)
        out_layers[pl][pc].append({
            "canonical": can,
            "aliases": [],
            "precision_tag": "phrase" if is_phrase(can) else "exact",
            "weight": score,
            "polarity": "negative" if pc == "pain_points" else "neutral",
        })
        seen.add(can.lower())

    refined = {
        "version": data.get("version", "v2.1"),
        "domain": data.get("domain", "crossborder"),
        "layers": out_layers,
    }
    return refined


def main() -> int:
    ap = argparse.ArgumentParser(description="Refine semantic sets and fill duplicates with candidates")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--candidates", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates.csv"))
    ap.add_argument("--output", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1_refined.yml"))
    args = ap.parse_args()

    data = load_lex(args.lexicon)
    before_total, before_unique = unique_terms(data)
    cands = load_candidates(args.candidates)
    out = refine_and_fill(data, cands)
    after_total, after_unique = unique_terms(out)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "before_total": before_total,
        "before_unique": before_unique,
        "after_total": after_total,
        "after_unique": after_unique,
        "output": str(args.output)
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

