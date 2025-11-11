#!/usr/bin/env python3
from __future__ import annotations

"""
Produce a small CSV of borderline alias decisions for human review.

Rules (borderline):
  - pending items only
  - jaro within +/-0.03 around threshold, or
  - cross-layer/cross-category but jaro >= threshold, or
  - high jaro (>=0.90) but cosine < 0.70

Output columns: canonical,layer,category,alias,jaro,cosine,ctx,suggested,reason
"""

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


HDR = re.compile(r"^##\s+(.+?)\s*\((L[1-4])/([a-z_]+)\)")


@dataclass
class Row:
    canonical: str
    layer: str
    category: str
    alias: str
    jaro: float
    cosine: float
    ctx: str
    decision: str


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
            try:
                cosine = float(parts[3])
            except Exception:
                cosine = 0.0
            ctx = parts[5]
            decision = (parts[6] or '').lower()
            if can:
                out.append(Row(canonical=can, layer=layer, category=cat, alias=alias, jaro=jaro, cosine=cosine, ctx=ctx, decision=decision))
    return out


def jaro_threshold(layer: str, category: str) -> float:
    if layer == 'L2' and category == 'brands':
        return 0.90
    if layer == 'L4' and category == 'pain_points':
        return 0.80
    return 0.85


def ctx_same(ctx: str) -> bool:
    try:
        sides = [s.strip() for s in ctx.split('/')]
        la = sides[0].split('→')[0].strip()
        lb = sides[0].split('→')[1].strip()
        ca = sides[1].split('→')[0].strip()
        cb = sides[1].split('→')[1].strip()
        return la == lb and ca == cb
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description='Produce borderline alias CSV for human review')
    ap.add_argument('--md', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    rows = parse_md(args.md)
    picks: List[Row] = []
    for r in rows:
        if r.decision and r.decision != 'pending':
            continue
        th = jaro_threshold(r.layer, r.category)
        near = abs(r.jaro - th) <= 0.03
        cross_ctx = (not ctx_same(r.ctx)) and (r.jaro >= th)
        high_jaro_low_cos = (r.jaro >= 0.90 and r.cosine < 0.70)
        if near or cross_ctx or high_jaro_low_cos:
            picks.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['canonical','layer','category','alias','jaro','cosine','ctx','suggested','reason'])
        for r in picks:
            th = jaro_threshold(r.layer, r.category)
            if ctx_same(r.ctx) and r.jaro >= th:
                suggested = 'approve'
                reason = f'same-layer&category, jaro>={th}'
            elif not ctx_same(r.ctx) and r.jaro >= th:
                suggested = 'reject'
                reason = 'cross-layer/category despite high jaro'
            else:
                suggested = 'review'
                reason = f'near-threshold ({r.jaro:.3f} vs {th})'
            w.writerow([r.canonical, r.layer, r.category, r.alias, f"{r.jaro:.3f}", f"{r.cosine:.3f}", r.ctx, suggested, reason])
    print(f"✅ Wrote borderline list: {args.out} ({len(picks)} rows)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

