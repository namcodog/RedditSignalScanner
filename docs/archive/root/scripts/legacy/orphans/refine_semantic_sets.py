#!/usr/bin/env python3
from __future__ import annotations

"""
Refine v2.1 semantic sets to improve uniqueness and remove weak/noisy terms.

Heuristics:
- Cross-layer deduplication: keep first occurrence order by layer priority L2>L3>L1>L4 for brands/features, L3>L2>L4>L1 for pain.
- Remove noisy tokens containing: amp/webp/png/http/.com
- Remove single-letter and token length < 3 (except whitelisted abbreviations)

Outputs a new JSON-as-YAML file and a small report with before/after stats.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Set


LAYER_PRIORITY = {
    "brands": ["L2", "L3", "L1", "L4"],
    "features": ["L2", "L3", "L1", "L4"],
    "pain_points": ["L3", "L2", "L4", "L1"],
}

NOISE_SUBSTR = [" amp", "webp", " png", ".com", " http"]
KEEP_ABBR = {"fba", "fbm", "ppc", "seo", "vat", "rfq", "moq", "qc", "3pl", "sku", "ctr", "cvr", "acos", "roas"}


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def refine(data: Dict) -> Dict:
    layers = data.get("layers", {})
    seen: Dict[str, Set[str]] = {"brands": set(), "features": set(), "pain_points": set()}
    out_layers: Dict[str, Dict[str, List[Dict]]] = {k: {"brands": [], "features": [], "pain_points": []} for k in ["L1", "L2", "L3", "L4"]}

    def noisy(s: str) -> bool:
        low = s.lower().strip()
        if any(ns in low for ns in NOISE_SUBSTR):
            return True
        if len(low) < 3 and low not in KEEP_ABBR:
            return True
        return False

    # Iterate by category with priority
    for cat, pri_layers in LAYER_PRIORITY.items():
        # collect terms sorted by priority
        bucket: List[tuple] = []
        for lay in pri_layers:
            for item in layers.get(lay, {}).get(cat, []):
                bucket.append((lay, item))
        for lay, item in bucket:
            can = str(item.get("canonical", "")).strip()
            if not can or noisy(can):
                continue
            key = can.lower()
            if key in seen[cat]:
                continue
            seen[cat].add(key)
            # keep item minimal fields
            out_layers[lay][cat].append({
                "canonical": can,
                "aliases": item.get("aliases", []),
                "precision_tag": item.get("precision_tag", "phrase"),
                "weight": item.get("weight", 1.0),
                "polarity": item.get("polarity", "neutral"),
            })

    refined = {
        "version": data.get("version", "v2.1"),
        "domain": data.get("domain", "crossborder"),
        "layers": out_layers,
    }
    return refined


def unique_count(d: Dict) -> int:
    terms: List[str] = []
    for cats in d.get("layers", {}).values():
        for arr in cats.values():
            terms.extend([str(x.get("canonical", "")).lower() for x in arr])
    return len(set(terms))


def main() -> int:
    ap = argparse.ArgumentParser(description="Refine v2.1 semantic sets")
    ap.add_argument("--input", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--output", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1_refined.yml"))
    args = ap.parse_args()

    data = load(args.input)
    before = unique_count(data)
    out = refine(data)
    after = unique_count(out)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "unique_before": before, "unique_after": after, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

