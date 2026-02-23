#!/usr/bin/env python3
from __future__ import annotations

"""
Evaluate entity dictionary coverage on a JSONL corpus.

Inputs:
  --dict backend/config/entity_dictionary/crossborder_v2.csv
  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl"
  --out backend/reports/local-acceptance/entity-metrics.csv

Outputs:
  - CSV with overall coverage, category coverage, top10 entities by post hits,
    and per-subreddit coverage rows.
  - Prints a compact JSON summary to stdout for quick checks.
"""

import argparse
import csv
import glob
import json
import re
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


def _load_dict(csv_path: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            term = (row.get("canonical") or "").strip()
            cat = (row.get("category") or "features").strip()
            if term:
                out.append((term, cat))
    return out


def _make_pattern(term: str) -> re.Pattern:
    t = term.strip()
    # phrase if whitespace, hyphen or slash
    if any(ch in t for ch in [" ", "-", "/"]):
        # use a simple case-insensitive substring regex with word-ish boundaries
        esc = re.escape(t)
        return re.compile(rf"(?i)\b{esc}\b")
    # single token -> exact word boundary match
    esc = re.escape(t)
    return re.compile(rf"(?i)\b{esc}\b")


def evaluate(dict_csv: Path, corpus_glob: str, out_csv: Path) -> Dict[str, object]:
    entries = _load_dict(dict_csv)
    patterns: List[Tuple[re.Pattern, str, str]] = []  # (pattern, term, category)
    for term, cat in entries:
        patterns.append((_make_pattern(term), term, cat))

    total_posts = 0
    matched_posts = 0
    matched_by_cat = {"brands": 0, "features": 0, "pain_points": 0}
    hits_per_term: Dict[str, int] = {}
    coverage_per_sub: Dict[str, int] = {}
    totals_per_sub: Dict[str, int] = {}

    files = [Path(p) for p in glob.glob(corpus_glob)]
    for fp in files:
        for obj in _iter_jsonl(fp):
            sub = str(obj.get("subreddit", "")).strip()
            totals_per_sub[sub] = totals_per_sub.get(sub, 0) + 1
            total_posts += 1
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()

            seen_any = False
            seen_cat = {"brands": False, "features": False, "pain_points": False}

            for pat, term, cat in patterns:
                if pat.search(text):
                    hits_per_term[term] = hits_per_term.get(term, 0) + 1
                    seen_any = True
                    seen_cat[cat] = True

            if seen_any:
                matched_posts += 1
                coverage_per_sub[sub] = coverage_per_sub.get(sub, 0) + 1
            for c, v in seen_cat.items():
                if v:
                    matched_by_cat[c] += 1

    # Summaries
    overall_cov = (matched_posts / total_posts) if total_posts else 0.0
    cat_cov = {k: (v / total_posts if total_posts else 0.0) for k, v in matched_by_cat.items()}
    top_terms = sorted(hits_per_term.items(), key=lambda x: -x[1])[:10]
    # Re-scan to compute unique coverage by top10 (union of posts matched by any top term)
    top_set = {t for t, _ in top_terms}
    top_patterns = [(p, t) for p, t, c in patterns if t in top_set]
    top_unique_posts = 0
    files = [Path(p) for p in glob.glob(corpus_glob)]
    for fp in files:
        for obj in _iter_jsonl(fp):
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            if any(p.search(text) for p, t in top_patterns):
                top_unique_posts += 1
    top10_unique_share = (top_unique_posts / matched_posts) if matched_posts else 0.0

    # Write CSV report (simple key/value lines + sections)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["total_posts", total_posts])
        w.writerow(["matched_posts", matched_posts])
        w.writerow(["coverage_overall", f"{overall_cov:.4f}"])
        for k, v in cat_cov.items():
            w.writerow([f"coverage_{k}", f"{v:.4f}"])
        w.writerow(["top10_unique_share", f"{top10_unique_share:.4f}"])
        w.writerow(["section", "top_terms"]) 
        w.writerow(["term", "post_hits"])
        for term, cnt in top_terms:
            w.writerow([term, cnt])
        w.writerow(["section", "coverage_by_subreddit"]) 
        w.writerow(["subreddit", "coverage", "total"]) 
        for sub, cov in sorted(coverage_per_sub.items(), key=lambda x: -x[1]):
            w.writerow([sub, cov, totals_per_sub.get(sub, 0)])

    return {
        "total_posts": total_posts,
        "matched_posts": matched_posts,
        "coverage_overall": overall_cov,
        "coverage_by_category": cat_cov,
        "top10_unique_share": top10_unique_share,
        "top_terms": top_terms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate entity dictionary coverage")
    ap.add_argument("--dict", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2.csv"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--out", type=Path, default=Path("backend/reports/local-acceptance/entity-metrics.csv"))
    args = ap.parse_args()

    res = evaluate(args.dict, args.corpus, args.out)
    print(json.dumps({
        "status": "ok",
        **res,
        "out": str(args.out)
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
