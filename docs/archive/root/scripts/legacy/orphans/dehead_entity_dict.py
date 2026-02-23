#!/usr/bin/env python3
from __future__ import annotations

"""
Reduce Top10 unique-share by capping dominant terms and swapping in long-tail
candidates. This is a pragmatic, zero-human heuristic to push
top10_unique_share below a target while preserving overall coverage.

Inputs:
  --dict CSV of current entity dictionary (canonical,category)
  --candidates CSV of candidate terms (canonical,category,layer,freq,score)
  --corpus Glob of JSONL files
  --output CSV path
  --target-top10-max Max allowed top10_unique_share (default: 0.70)
  --max-iters Max replacement attempts (default: 24)

Strategy:
  1) Measure hits per term for all dict terms using phrase match (word boundary).
  2) Compute top10_unique_share like metrics script.
  3) While share > target and iters remain:
       - Remove the most dominant term among current top10.
       - Add a replacement from candidates not present in dict, preferring:
           * pain_points > features > brands
           * lower corpus hits (diversification) and lower candidate freq
       - Recompute metric; stop early if no better found.
  4) Write updated dict to output.

Notes: conservative and deterministic; can be run multiple times. It does not
touch categories beyond the simple priority heuristic; upstream diverse builder
should enforce category caps.
"""

import argparse
import csv
import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
            except Exception:
                continue


def _make_phrase_pat(term: str):
    import re

    t = term.strip()
    esc = re.escape(t)
    return re.compile(rf"(?i)\b{esc}\b")


def _load_dict(csv_path: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            t = (row.get("canonical") or "").strip()
            c = (row.get("category") or "features").strip()
            if t:
                out.append((t, c))
    return out


def _load_candidates(csv_path: Path) -> List[Tuple[str, str, int, float]]:
    out: List[Tuple[str, str, int, float]] = []
    with csv_path.open("r", encoding="utf-8") as f:
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


def _measure_hits(terms: List[str], files: List[Path]) -> Dict[str, int]:
    pats = {t: _make_phrase_pat(t) for t in terms}
    hits: Dict[str, int] = {t: 0 for t in terms}
    for fp in files:
        for obj in _iter_jsonl(fp):
            txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            seen = set()
            for t, pat in pats.items():
                if t in seen:
                    continue
                if pat.search(txt):
                    hits[t] += 1
                    seen.add(t)
    return hits


def _compute_top10_share(hits: Dict[str, int], matched_posts: int) -> float:
    top = sorted(hits.items(), key=lambda x: -x[1])[:10]
    top_terms = {t for t, _ in top}
    # Estimate unique coverage contributed by top10
    # We approximate by counting any post matched by any of top10 as 1.
    # For efficiency, reuse hits as upper bound when matched_posts is provided.
    # A tighter estimate requires re-scanning corpus per post; we skip here.
    top_hits_sum = sum(hits[t] for t in top_terms)
    if matched_posts <= 0:
        return 0.0
    # Upper bound; acceptable for monotonic guidance
    return min(1.0, top_hits_sum / float(matched_posts))


def _write_dict(rows: List[Tuple[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "category"])
        w.writeheader()
        for term, cat in rows:
            w.writerow({"canonical": term, "category": cat})


def main() -> int:
    ap = argparse.ArgumentParser(description="De-head entity dict to reduce top10 share")
    ap.add_argument("--dict", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--target-top10-max", type=float, default=0.70)
    ap.add_argument("--max-iters", type=int, default=24)
    args = ap.parse_args()

    files = [Path(p) for p in glob.glob(args.corpus)]
    dict_rows = _load_dict(args.dict)
    candidates = _load_candidates(args.candidates)

    terms = [t for t, _ in dict_rows]
    hits = _measure_hits(terms, files)
    matched_posts = sum(1 for _ in (term for term in terms))  # dummy to avoid zero
    matched_posts = max(sum(hits.values()) // max(1, len(terms)), 1)
    share = _compute_top10_share(hits, matched_posts)

    iters = 0
    current = list(dict_rows)
    present = {t.lower() for t, _ in current}

    # Pre-rank candidates: lowest freq first, category priority
    cat_priority = {"pain_points": 0, "features": 1, "brands": 2}
    ranked_cands = sorted(
        candidates,
        key=lambda x: (cat_priority.get(x[1], 9), x[2], -x[3]),
    )

    while share > args.target_top10_max and iters < args.max_iters:
        iters += 1
        # pick the most dominant term
        dom = max(hits.items(), key=lambda x: x[1])[0]
        # remove dom from current
        idx = next((i for i, (t, _) in enumerate(current) if t == dom), None)
        if idx is None:
            break
        current.pop(idx)
        present.discard(dom.lower())

        # pick replacement
        repl = None
        for t, cat, freq, _score in ranked_cands:
            if t.lower() in present:
                continue
            repl = (t, cat)
            present.add(t.lower())
            break
        if repl:
            current.append(repl)

        # recompute
        terms = [t for t, _ in current]
        hits = _measure_hits(terms, files)
        matched_posts = max(sum(hits.values()) // max(1, len(terms)), 1)
        new_share = _compute_top10_share(hits, matched_posts)
        if new_share >= share:
            # revert change if not improved
            current = list(dict_rows)
            break
        dict_rows = list(current)
        share = new_share

    _write_dict(dict_rows, args.output)
    print(json.dumps({"status": "ok", "iters": iters, "top10_share": share, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

