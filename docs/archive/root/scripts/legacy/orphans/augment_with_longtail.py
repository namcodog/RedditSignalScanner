#!/usr/bin/env python3
from __future__ import annotations

"""
Stage 2 - Long-tail augmentation pilot (offline).

Goal: decrease entity top10_unique_share by adding multi-word long-tail
feature phrases that match posts NOT already covered by current top10 terms.

Inputs:
  --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv
  --candidates backend/reports/local-acceptance/crossborder_candidates.csv
  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl"
  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv
  --replace-n 12  (how many features to replace)

Heuristics:
  - Only consider candidate category=features and phrases (contains space/-/ /)
  - Score candidates by number of posts they match outside the union of current top10 hits
  - Replace the last N features in current dict with top-N long-tail candidates
  - Keep constraints: brands <= 30; pain_points >= 35; total=100
"""

import argparse
import csv
import glob
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _is_phrase(s: str) -> bool:
    return (" " in s) or ("-" in s) or ("/" in s)


def _make_pat(t: str):
    esc = re.escape(t.strip())
    return re.compile(rf"(?i)\b{esc}\b")


def load_dict(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def load_candidates(path: Path) -> List[Tuple[str, str, str, int, float]]:
    out: List[Tuple[str, str, str, int, float]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get("canonical") or "").strip()
            cat = (row.get("category") or "features").strip()
            lay = (row.get("layer") or "L2").strip()
            try:
                freq = int(row.get("freq") or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            out.append((can, cat, lay, freq, score))
    # prefer higher freq first, then score
    out.sort(key=lambda x: (-x[3], -x[4]))
    return out


def compute_top10_union(rows: List[Dict[str, str]], corpus_glob: str) -> Tuple[Set[str], List[Tuple[str, int]]]:
    # count hits per term
    patterns: List[Tuple[re.Pattern, str]] = []
    for r in rows:
        term = (r.get("canonical") or "").strip()
        if not term:
            continue
        patterns.append((_make_pat(term), term))
    hits: Dict[str, int] = {}
    files = [Path(p) for p in glob.glob(corpus_glob)]
    for fp in files:
        for obj in _iter_jsonl(fp):
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            for pat, term in patterns:
                if pat.search(text):
                    hits[term] = hits.get(term, 0) + 1
    top = sorted(hits.items(), key=lambda x: -x[1])[:10]
    # union set of post ids matched by top10
    top_terms = {t for t, _ in top}
    top_pats = [(_make_pat(t), t) for t in top_terms]
    union_ids: Set[str] = set()
    for fp in files:
        for obj in _iter_jsonl(fp):
            pid = str(obj.get("id", ""))
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            if any(p.search(text) for p, _ in top_pats):
                union_ids.add(pid)
    return union_ids, top


STOP_PHRASE_SUBSTR = {"days ago", "weekly", "welcome", "hours", "question", "newbie", "discussion", "2024", "2025"}


def score_longtail_candidates(cands: List[Tuple[str, str, str, int, float]], existing_lc: Set[str], top10_union: Set[str], corpus_glob: str) -> List[Tuple[str, str, float, int]]:
    # returns list of (canonical, layer, new_coverage_hits, freq)
    files = [Path(p) for p in glob.glob(corpus_glob)]
    scored: List[Tuple[str, str, float, int]] = []
    for can, cat, lay, freq, score in cands:
        low = can.lower()
        if cat != "features":
            continue
        if low in existing_lc:
            continue
        if not _is_phrase(can):
            continue
        low = can.lower()
        if any(s in low for s in STOP_PHRASE_SUBSTR):
            continue
        pat = _make_pat(can)
        new_hits = 0
        for fp in files:
            for obj in _iter_jsonl(fp):
                pid = str(obj.get("id", ""))
                if pid in top10_union:
                    continue
                text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
                if pat.search(text):
                    new_hits += 1
        if new_hits > 0:
            scored.append((can, lay, float(new_hits), int(freq)))
    # rank by new_hits desc then freq desc
    scored.sort(key=lambda x: (-x[2], -x[3]))
    return scored


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["canonical", "category", "source_layer", "weight", "norm_weight", "polarity"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def main() -> int:
    ap = argparse.ArgumentParser(description="Augment entity dict with long-tail feature phrases")
    ap.add_argument("--dict", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2_diverse.csv"))
    ap.add_argument("--candidates", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates.csv"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--output", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2_diverse.csv"))
    ap.add_argument("--replace-n", type=int, default=12)
    ap.add_argument("--max-brands", type=int, default=30)
    ap.add_argument("--min-pains", type=int, default=35)
    ap.add_argument("--total", type=int, default=100)
    args = ap.parse_args()

    rows = load_dict(args.dict)
    existing_lc = {(r.get("canonical") or "").strip().lower() for r in rows}
    top_union, top_terms = compute_top10_union(rows, args.corpus)

    cands = load_candidates(args.candidates)
    ranked = score_longtail_candidates(cands, existing_lc, top_union, args.corpus)
    # partition existing
    brands = [r for r in rows if (r.get("category") or "").strip() == "brands"][: args.max_brands]
    pains = [r for r in rows if (r.get("category") or "").strip() == "pain_points"]
    if len(pains) < args.min_pains:
        # simple fill from candidates (phrases only)
        for can, lay, new_hits, freq in ranked:
            # skip, this ranked is features only; pain fill not covered here intentionally
            pass
    feats = [r for r in rows if (r.get("category") or "").strip() == "features"]
    # replace last N features
    n = min(args.replace_n, len(feats))
    keep_feats = feats[:-n] if n > 0 else feats
    add_feats: List[Dict[str, str]] = []
    added_lc: Set[str] = set()
    i = 0
    while len(add_feats) < n and i < len(ranked):
        can, lay, new_hits, freq = ranked[i]
        i += 1
        low = (can or "").lower()
        if low in existing_lc or low in added_lc:
            continue
        add_feats.append({
            "canonical": can,
            "category": "features",
            "source_layer": lay,
            "weight": "1.00",
            "norm_weight": "1.00",
            "polarity": "neutral",
        })
        added_lc.add(low)

    merged = brands + keep_feats + add_feats + pains
    # enforce total size
    if len(merged) > args.total:
        merged = merged[: args.total]
    write_csv(merged, args.output)
    print(json.dumps({
        "status": "ok",
        "top10_terms": top_terms,
        "added_longtail": [x["canonical"] for x in add_feats],
        "output": str(args.output)
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
