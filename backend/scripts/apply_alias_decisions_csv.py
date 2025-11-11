#!/usr/bin/env python3
from __future__ import annotations

"""
Apply decisions from a CSV (boundary review) into alias_map.csv.

Input CSV columns: canonical,layer,category,alias,decision,notes
Only rows with non-empty 'decision' will be applied.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def main() -> int:
    ap = argparse.ArgumentParser(description='Apply alias decisions from CSV into alias_map.csv')
    ap.add_argument('--decisions', type=Path, required=True)
    ap.add_argument('--csv', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    # load decisions
    decs: Dict[tuple, tuple] = {}
    with args.decisions.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            decision = (row.get('decision') or '').strip()
            notes = (row.get('notes') or '').strip()
            if not decision:
                continue
            key = ((row.get('canonical') or '').strip().lower(), (row.get('alias') or '').strip().lower())
            decs[key] = (decision, notes)

    in_rows: List[Dict[str, str]] = []
    with args.csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            in_rows.append(row)

    updated = 0
    for row in in_rows:
        key = ((row.get('canonical') or '').strip().lower(), (row.get('alias') or '').strip().lower())
        if key in decs:
            row['decision'], row['notes'] = decs[key]
            updated += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(in_rows[0].keys()) if in_rows else [])
        w.writeheader()
        for r in in_rows:
            w.writerow(r)
    print(f"✅ Applied {updated} decisions -> {args.out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

