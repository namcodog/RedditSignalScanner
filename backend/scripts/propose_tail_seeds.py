#!/usr/bin/env python3
from __future__ import annotations

"""
Propose long-tail (tail) phrase seeds from existing candidates by measuring
how many of their matches come from posts OUTSIDE the current Top10 union.

Usage:
  python -u backend/scripts/propose_tail_seeds.py \
    --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
    --entity backend/config/entity_dictionary/crossborder_v2_diverse.csv \
    --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
    --out backend/reports/local-acceptance/tail_seeds_proposed.csv \
    --min-tail-ratio 0.5 --per-layer 30 --min-freq 10 --max-freq 200

Output CSV columns:
  canonical,layer,category,tail_ratio,tail_hits,total_hits,freq,score,reason,decision,notes
  - decision/notes 供人工标注（留空即可；你只需对要保留的行填决策）
"""

import argparse
import csv
import glob
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


GENERIC = {
    'help','new','time','people','need','thanks','using','online','page','site','www','email','year','month','day','better',
    'product','products','store','stores','brand','brands','marketing','ad','ads','company','business','sell','selling','sales','customer','customers','account',
    'shipping','items','item','start','commerce','dropshipping','ecommerce'
}
STOP_PHRASE_SUBSTR = {
    'days ago','weekly','welcome','hours','question','newbie','discussion','thank','thanks','advance','pls','please','anyone know','trying figure','looking forward'
}
KNOWN_BRANDS = {'amazon','shopify','tiktok','facebook','meta','instagram','google','aliexpress','alibaba','klaviyo','stripe','paypal','dhl','fedex','ups'}


def _iter_jsonl(path: Path):
    with path.open('r', encoding='utf-8') as f:
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


def _make_pat(term: str) -> re.Pattern[str]:
    esc = re.escape(term.strip())
    return re.compile(rf"(?i)\b{esc}\b")


def is_phrase(s: str) -> bool:
    return (' ' in s) or ('-' in s) or ('/' in s)


def split_tokens(s: str):
    for t in re.split(r"\s+|[-/]+", s):
        t = t.strip()
        if t:
            yield t


def load_candidates(path: Path) -> List[Tuple[str, str, int, float]]:
    out: List[Tuple[str, str, int, float]] = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get('canonical') or '').strip()
            layer = (row.get('layer') or 'L2').strip()
            try:
                freq = int(row.get('freq') or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get('score') or 0.0)
            except Exception:
                score = 0.0
            if can:
                out.append((can, layer, freq, score))
    # rank by score then freq
    out.sort(key=lambda x: (-x[3], -x[2]))
    return out


def load_entity(path: Path) -> List[str]:
    terms: List[str] = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            t = (row.get('canonical') or '').strip()
            if t:
                terms.append(t)
    return terms


def compute_top10_union(entity_terms: List[str], corpus_glob: str) -> Tuple[Set[str], List[Tuple[str, int]]]:
    # count hits per term
    patterns = [(_make_pat(t), t) for t in entity_terms]
    hits: Dict[str, int] = {}
    files = [Path(p) for p in glob.glob(corpus_glob)]
    for fp in files:
        for obj in _iter_jsonl(fp):
            txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            for pat, term in patterns:
                if pat.search(txt):
                    hits[term] = hits.get(term, 0) + 1
    top = sorted(hits.items(), key=lambda x: -x[1])[:10]
    top_set = {t for t, _ in top}
    top_pats = [(_make_pat(t), t) for t in top_set]
    union: Set[str] = set()
    for fp in files:
        for obj in _iter_jsonl(fp):
            pid = str(obj.get('id', ''))
            txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            if any(p.search(txt) for p, _ in top_pats):
                union.add(pid)
    return union, top


def main() -> int:
    ap = argparse.ArgumentParser(description='Propose tail seeds from candidates')
    ap.add_argument('--candidates', type=Path, default=Path('backend/reports/local-acceptance/crossborder_candidates.csv'))
    ap.add_argument('--entity', type=Path, default=Path('backend/config/entity_dictionary/crossborder_v2_diverse.csv'))
    ap.add_argument('--corpus', default='backend/data/snapshots/2025-11-07-0.2/*.jsonl')
    ap.add_argument('--out', type=Path, default=Path('backend/reports/local-acceptance/tail_seeds_proposed.csv'))
    ap.add_argument('--min-tail-ratio', type=float, default=0.5)
    ap.add_argument('--per-layer', type=int, default=30)
    ap.add_argument('--min-freq', type=int, default=10)
    ap.add_argument('--max-freq', type=int, default=200)
    args = ap.parse_args()

    cands = load_candidates(args.candidates)
    ent_terms = load_entity(args.entity)
    top_union, top_pairs = compute_top10_union(ent_terms, args.corpus)

    files = [Path(p) for p in glob.glob(args.corpus)]
    rows: List[Dict[str, object]] = []
    per_layer_count: Dict[str, int] = {'L2': 0, 'L3': 0, 'L4': 0}
    for can, layer, freq, score in cands:
        low = can.lower()
        if layer not in per_layer_count:
            continue
        if per_layer_count[layer] >= args.per_layer:
            continue
        # filters
        if not is_phrase(can):
            continue
        toks = list(split_tokens(low))
        if any(t in GENERIC for t in toks):
            continue
        if any(t in KNOWN_BRANDS for t in toks):
            continue
        if any(s in low for s in STOP_PHRASE_SUBSTR):
            continue
        if not (args.min_freq <= freq <= args.max_freq):
            continue
        # compute hits
        pat = _make_pat(can)
        total_hits = 0
        tail_hits = 0
        for fp in files:
            for obj in _iter_jsonl(fp):
                pid = str(obj.get('id', ''))
                txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
                if pat.search(txt):
                    total_hits += 1
                    if pid not in top_union:
                        tail_hits += 1
        if total_hits == 0:
            continue
        tail_ratio = tail_hits / total_hits
        if tail_ratio < max(0.0, min(1.0, args.min_tail_ratio)):
            continue
        rows.append({
            'canonical': can,
            'layer': layer,
            'category': 'features',
            'tail_ratio': round(tail_ratio, 3),
            'tail_hits': tail_hits,
            'total_hits': total_hits,
            'freq': freq,
            'score': score,
            'reason': 'tail_ratio_ok; phrase; non-generic; non-brand',
            'decision': '',
            'notes': '',
        })
        per_layer_count[layer] += 1

    # sort by tail_hits desc then tail_ratio desc
    rows.sort(key=lambda x: (-int(x['tail_hits']), -float(x['tail_ratio'])))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['canonical','layer','category','tail_ratio','tail_hits','total_hits','freq','score','reason','decision','notes'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps({'proposed': len(rows), 'out': str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

