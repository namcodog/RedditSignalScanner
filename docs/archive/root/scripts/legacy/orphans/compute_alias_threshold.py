#!/usr/bin/env python3
from __future__ import annotations

"""Compute an adaptive alias score threshold from alias_map.csv.

Strategy: take a conservative quantile (default q=0.95) of the score column,
then clamp to a minimum floor (default 0.90). Prints the threshold to stdout.
"""

import argparse
import csv
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute adaptive alias threshold")
    ap.add_argument("--alias-map", type=Path, required=True)
    ap.add_argument("--quantile", type=float, default=0.95)
    ap.add_argument("--min-floor", type=float, default=0.90)
    args = ap.parse_args()

    scores: list[float] = []
    with args.alias_map.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                s = float(row.get("score") or 0.0)
                if s > 0:
                    scores.append(s)
            except Exception:
                continue
    if not scores:
        print(f"{args.min_floor:.2f}")
        return 0
    scores.sort()
    k = max(0, min(len(scores) - 1, int(round(args.quantile * (len(scores) - 1)))))
    thr = max(args.min_floor, scores[k])
    print(f"{thr:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

