#!/usr/bin/env python3
from __future__ import annotations

"""
Score a corpus using HybridMatcher and the v2.1 semantic lexicon (layers).

Inputs:
  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml
  --corpus  "backend/data/snapshots/2025-11-07-0.2/*.jsonl"
  --limit-per-sub 20

Outputs:
  backend/reports/local-acceptance/hybrid_score_summary.csv

This is a lightweight local evaluator that does not touch external APIs.
"""

import argparse
import csv
import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from app.services.analysis.hybrid_matcher import HybridMatcher, Term


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


def _load_lex_v21(path: Path) -> Dict[str, List[Term]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    out: Dict[str, List[Term]] = {}
    for layer, cats in layers.items():
        arr: List[Term] = []
        for cat, items in cats.items():
            for it in items:
                arr.append(
                    Term(
                        canonical=str(it.get("canonical", "")),
                        aliases=list(it.get("aliases", [])),
                        precision_tag=str(it.get("precision_tag", "phrase")),
                        category=cat,
                        weight=float(it.get("weight", 1.0)),
                    )
                )
        out[layer] = arr
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid score with v2.1 lexicon")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--limit-per-sub", type=int, default=20)
    args = ap.parse_args()

    lex = _load_lex_v21(args.lexicon)
    files = [Path(p) for p in glob.glob(args.corpus)]

    # group texts by subreddit and layer mapping
    layer_by_sub = {
        "ecommerce": "L1",
        "AmazonSeller": "L2",
        "Shopify": "L2",
        "dropship": "L3",
        "dropshipping": "L4",
    }

    texts_by_layer: Dict[str, List[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}
    for fp in files:
        sub = fp.stem
        layer = layer_by_sub.get(sub)
        if not layer:
            continue
        cnt = 0
        for obj in _iter_jsonl(fp):
            text = f"{obj.get('title','')} {obj.get('selftext','')}".strip()
            if not text:
                continue
            texts_by_layer[layer].append(text)
            cnt += 1
            if cnt >= args.limit_per_sub:
                break

    out_rows: List[Dict[str, object]] = []
    for layer, terms in lex.items():
        m = HybridMatcher(terms, enable_semantic=False)
        texts = texts_by_layer.get(layer, [])
        total = len(texts)
        hits = 0
        for txt in texts:
            res = m.match_text(txt)
            if res:
                hits += 1
        out_rows.append({"layer": layer, "posts": total, "hit_posts": hits, "coverage": round(hits / max(1, total), 4)})

    out_path = Path("backend/reports/local-acceptance/hybrid_score_summary.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["layer", "posts", "hit_posts", "coverage"])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(json.dumps({"status": "ok", "rows": out_rows, "output": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
