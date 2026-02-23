#!/usr/bin/env python3
from __future__ import annotations

"""
Prepare a next batch of mid-frequency multi-word feature phrases per layer to reduce Top10 dominance.

Filters:
  - category == features
  - phrase only (space / '-' / '/')
  - freq in [--freq-min, --freq-max]
  - exclude generic tokens and obvious brands

Selection:
  - per-layer top by score then freq
  - limit per-layer via --per-layer

Outputs CSV with: canonical,layer,category,freq,score,reason
"""

import argparse
import csv
from pathlib import Path
from typing import List, Tuple


GENERIC = {
    'help','new','time','people','need','thanks','using','online','page','site','www','email','year','month','day','better',
    'product','products','store','stores','brand','brands','marketing','ad','ads','company','business','sell','selling','sales','customer','customers','account',
    'shipping','items','item','start','commerce','dropshipping','ecommerce'
}
STOP_PHRASE_SUBSTR = {
    'days ago','weekly','welcome','hours','question','newbie','discussion','thank','thanks','advance','pls','please','anyone know','trying figure','looking forward'
}

KNOWN_BRANDS = {'amazon','shopify','tiktok','facebook','meta','instagram','google','aliexpress','alibaba','klaviyo','stripe','paypal','dhl','fedex','ups'}


def is_phrase(s: str) -> bool:
    return (' ' in s) or ('-' in s) or ('/' in s)


def load_candidates(path: Path) -> List[Tuple[str,str,str,int,float]]:
    out: List[Tuple[str,str,str,int,float]] = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get('canonical') or '').strip()
            cat = (row.get('category') or 'features').strip()
            lay = (row.get('layer') or 'L2').strip()
            try:
                freq = int(row.get('freq') or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get('score') or 0.0)
            except Exception:
                score = 0.0
            out.append((can, cat, lay, freq, score))
    out.sort(key=lambda x: (-x[4], -x[3]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='Prepare next batch mid-frequency phrases per layer')
    ap.add_argument('--candidates', type=Path, default=Path('backend/reports/local-acceptance/crossborder_candidates.csv'))
    ap.add_argument('--out', type=Path, default=Path('backend/reports/local-acceptance/next_batch_phrases.csv'))
    ap.add_argument('--per-layer', type=int, default=15)
    ap.add_argument('--freq-min', type=int, default=20)
    ap.add_argument('--freq-max', type=int, default=150)
    args = ap.parse_args()

    rows = load_candidates(args.candidates)
    picked = []
    seen = set()
    layers = ['L2','L3','L4']  # focus on downstream layers for de-heading
    counts = {l: 0 for l in layers}
    for can, cat, lay, freq, score in rows:
        low = can.lower()
        if cat != 'features':
            continue
        if lay not in layers:
            continue
        if not is_phrase(can):
            continue
        if not (args.freq_min <= freq <= args.freq_max):
            continue
        # exclude obvious generic/brands
        toks = [t for t in re_split_tokens(low)]
        if any(t in GENERIC for t in toks):
            continue
        if any(t in KNOWN_BRANDS for t in toks):
            continue
        if any(s in low for s in STOP_PHRASE_SUBSTR):
            continue
        if low in seen:
            continue
        if counts[lay] >= args.per_layer:
            continue
        reason = f"mid-frequency {freq}; phrase; features; layer={lay}"
        picked.append((can, lay, 'features', freq, score, reason))
        seen.add(low)
        counts[lay] += 1
        if all(counts[l] >= args.per_layer for l in layers):
            break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['canonical','layer','category','freq','score','reason'])
        for r in picked:
            w.writerow(list(r))
    print(f"✅ Wrote next batch phrases: {args.out} ({len(picked)} rows), per-layer={args.per_layer}")
    return 0


def re_split_tokens(s: str):
    import re
    for t in re.split(r"\s+|[-/]+", s):
        t = t.strip()
        if t:
            yield t


if __name__ == '__main__':
    raise SystemExit(main())
