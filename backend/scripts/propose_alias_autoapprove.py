#!/usr/bin/env python3
from __future__ import annotations

"""
Scan alias_suggestions.md and propose high-confidence auto-approve candidates
based on Spec 011 thresholds and context alignment (same layer & category).

Usage:
  python -u backend/scripts/propose_alias_autoapprove.py \
    --md backend/reports/local-acceptance/alias_suggestions.md \
    --out backend/reports/local-acceptance/alias_autoapprove.csv
"""

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Row:
    canonical: str
    layer: str
    category: str
    alias: str
    jaro: float
    ctx: str
    decision: str
    notes: str


HDR = re.compile(r"^##\s+(.+?)\s*\((L[1-4])/([a-z_]+)\)")


def parse_md(p: Path) -> List[Row]:
    out: List[Row] = []
    can = layer = cat = ""
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            m = HDR.match(line.strip())
            if m:
                can, layer, cat = m.group(1).strip(), m.group(2), m.group(3)
                continue
            if not line.strip().startswith("|"):
                continue
            parts = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(parts) < 8 or parts[0] == 'alias':
                continue
            alias = parts[0]
            try:
                jaro = float(parts[2])
            except Exception:
                jaro = 0.0
            ctx = parts[5]
            decision = (parts[6] or '').lower()
            notes = parts[7]
            if can:
                out.append(Row(canonical=can, layer=layer, category=cat, alias=alias, jaro=jaro, ctx=ctx, decision=decision, notes=notes))
    return out


def ctx_same(ctx: str) -> bool:
    # expects: "Lx→Ly / catA→catB"
    try:
        sides = [s.strip() for s in ctx.split('/')]
        la = sides[0].split('→')[0].strip()
        lb = sides[0].split('→')[1].strip()
        ca = sides[1].split('→')[0].strip()
        cb = sides[1].split('→')[1].strip()
        return la == lb and ca == cb
    except Exception:
        return False


def jaro_ok(jaro: float, layer: str, category: str) -> bool:
    if layer == 'L2' and category == 'brands':
        return jaro >= 0.90
    if layer == 'L4' and category == 'pain_points':
        return jaro >= 0.80
    return jaro >= 0.85


def main() -> int:
    ap = argparse.ArgumentParser(description='Propose auto-approve alias suggestions')
    ap.add_argument('--md', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    rows = parse_md(args.md)
    picks: List[Row] = []
    for r in rows:
        if r.decision and r.decision != 'pending':
            continue
        if not ctx_same(r.ctx):
            continue
        if not jaro_ok(r.jaro, r.layer, r.category):
            continue
        picks.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['canonical','layer','category','alias','jaro','ctx','suggested_decision','reason'])
        for r in picks:
            w.writerow([r.canonical, r.layer, r.category, r.alias, f"{r.jaro:.3f}", r.ctx, 'approve', 'same-layer&category + jaro>=threshold'])
    print(f"✅ Proposed {len(picks)} auto-approve suggestions -> {args.out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

