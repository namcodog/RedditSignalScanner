#!/usr/bin/env python3
from __future__ import annotations

"""Filter alias_map.csv rows by a minimum score threshold.

Outputs a CSV with the same header and only rows with score >= threshold.
"""

import argparse
import csv
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Filter alias map by score")
    ap.add_argument("--alias-map", type=Path, required=True)
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    with args.alias_map.open("r", encoding="utf-8") as f_in, args.output.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            try:
                s = float(row.get("score") or 0.0)
            except Exception:
                s = 0.0
            if s >= args.threshold:
                writer.writerow(row)
    print(f"✅ filtered alias_map → {args.output} (threshold={args.threshold})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

