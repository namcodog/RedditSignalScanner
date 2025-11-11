#!/usr/bin/env python3
from __future__ import annotations

"""
Compare two entity-metrics CSVs produced by evaluate_entity_dict.py and
write a compact diff CSV highlighting key metrics and top terms examples.

Usage:
  python -u backend/scripts/diff_entity_metrics.py \
    --base backend/reports/local-acceptance/entity-metrics.csv \
    --new backend/reports/local-acceptance/entity-metrics_diverse.csv \
    --out backend/reports/local-acceptance/metrics/metrics_diversity_diff.csv
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple


def load_metrics(path: Path) -> Dict[str, object]:
    metrics: Dict[str, object] = {}
    top_terms: List[Tuple[str, int]] = []
    section = ""
    with path.open("r", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if not row:
                continue
            if row[0] == "section":
                section = row[1]
                continue
            if section == "":
                # key/value line
                if len(row) >= 2:
                    metrics[row[0]] = row[1]
            elif section == "top_terms":
                if row[0] == "term":
                    continue
                if len(row) >= 2:
                    try:
                        top_terms.append((row[0], int(row[1])))
                    except Exception:
                        continue
            # ignore coverage_by_subreddit for diff
    metrics["top_terms"] = top_terms
    return metrics


def write_diff(base: Dict[str, object], new: Dict[str, object], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = [
        "coverage_overall",
        "coverage_brands",
        "coverage_features",
        "coverage_pain_points",
        "top10_unique_share",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "baseline", "diverse", "delta"])
        for k in keys:
            b = float(base.get(k, 0.0)) if isinstance(base.get(k), str) else float(base.get(k, 0.0))
            n = float(new.get(k, 0.0)) if isinstance(new.get(k), str) else float(new.get(k, 0.0))
            w.writerow([k, f"{b:.4f}", f"{n:.4f}", f"{(n-b):+.4f}"])
        # Top terms samples
        w.writerow(["section", "top_terms_baseline"])
        w.writerow(["term", "post_hits"])
        for t, c in base.get("top_terms", [])[:10]:
            w.writerow([t, c])
        w.writerow(["section", "top_terms_diverse"])
        w.writerow(["term", "post_hits"])
        for t, c in new.get("top_terms", [])[:10]:
            w.writerow([t, c])


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff two entity-metrics CSVs")
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    base = load_metrics(args.base)
    new = load_metrics(args.new)
    write_diff(base, new, args.out)
    print(f"✅ wrote diff to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

