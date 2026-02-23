#!/usr/bin/env python3
from __future__ import annotations

"""
Suggest generic/low-signal terms for blacklist based on entity metrics CSV.

Heuristics:
  - very short tokens (len<=3) unless brand category
  - dictionary-like generic words from a small stoplist (issue, problem, price, etc.)
  - tokens containing spaces but lacking alphanumerics are ignored

Inputs:
  --metrics-csv entity-metrics_*.csv from evaluate_entity_dict.py
  --out path to write suggestions (txt)
"""

import argparse
import csv
import re
from pathlib import Path

GENERIC = {
    "issue", "issues", "problem", "problems", "price", "prices", "help",
    "need", "question", "thanks", "today", "yesterday", "tomorrow",
    "good", "bad", "best", "worst", "new", "old", "first", "last",
    "free", "shipping", "buy", "sell", "store",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Suggest blacklist terms from metrics")
    ap.add_argument("--metrics-csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    terms: list[str] = []
    mode = None
    with args.metrics_csv.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0] == "section" and len(row) > 1:
                mode = row[1]
                continue
            if mode == "top_terms" and len(row) >= 2 and row[0] != "term":
                term = row[0].strip().lower()
                if not term:
                    continue
                if re.search(r"[a-z0-9]", term) is None:
                    continue
                if len(term) <= 3 and term not in {"seo", "sem", "ppc"}:
                    terms.append(term)
                if term in GENERIC:
                    terms.append(term)

    uniq = sorted(set(terms))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8")
    print(f"✅ blacklist suggestions → {args.out} ({len(uniq)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

