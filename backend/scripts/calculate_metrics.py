#!/usr/bin/env python3
from __future__ import annotations

"""
Stage 2 - Quality metrics generator for semantic lexicon and entity dictionary.

Computes lightweight, reproducible metrics on local corpus without network:
- Coverage@Post (HybridMatcher based) overall and by layer
- Coverage@Category (brands/features/pain_points)
- Top10 unique-coverage share (entity dict)
- Unique@500 (unique canonical terms in semantic_sets)
- Drift (optional): compares with previous JSON snapshot if provided

Outputs CSV + JSON snapshot under reports/local-acceptance/metrics/.
"""

import argparse
import csv
import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from app.services.analysis.hybrid_matcher import HybridMatcher, Term
import os
import json as _json


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


def _load_lexicon_v21(path: Path) -> Dict[str, List[Term]]:
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


def _load_entity_dict(csv_path: Path) -> List[Tuple[str, str]]:
    import csv as _csv

    if not csv_path.exists():
        return []
    out: List[Tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = _csv.DictReader(f)
        for row in r:
            t = (row.get("canonical") or "").strip()
            c = (row.get("category") or "features").strip()
            if t:
                out.append((t, c))
    return out


def _make_phrase_pat(term: str):
    import re

    t = term.strip()
    esc = re.escape(t)
    if any(ch in t for ch in [" ", "-", "/"]):
        return re.compile(rf"(?i)\b{esc}\b")
    return re.compile(rf"(?i)\b{esc}\b")


def compute_entity_coverage(entity_csv: Path, corpus_glob: str) -> Dict[str, float | int]:
    pairs = _load_entity_dict(entity_csv)
    if not pairs:
        return {"overall": 0.0, "brands": 0.0, "features": 0.0, "pain_points": 0.0, "top10_unique_share": 0.0}

    patterns = [(_make_phrase_pat(t), t, c) for (t, c) in pairs]
    files = [Path(p) for p in glob.glob(corpus_glob)]

    total = 0
    matched = 0
    by_cat = {"brands": 0, "features": 0, "pain_points": 0}
    hits_per = {}
    for fp in files:
        for obj in _iter_jsonl(fp):
            total += 1
            txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            seen_any = False
            seen_cat = {"brands": False, "features": False, "pain_points": False}
            for pat, term, cat in patterns:
                if pat.search(txt):
                    hits_per[term] = hits_per.get(term, 0) + 1
                    seen_any = True
                    seen_cat[cat] = True
            if seen_any:
                matched += 1
            for c, v in seen_cat.items():
                if v:
                    by_cat[c] += 1

    # top10 unique share
    top10 = sorted(hits_per.items(), key=lambda x: -x[1])[:10]
    top_terms = {t for t, _ in top10}
    top_unique = 0
    for fp in files:
        for obj in _iter_jsonl(fp):
            txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            if any(_make_phrase_pat(t).search(txt) for t in top_terms):
                top_unique += 1
    return {
        "overall": matched / max(1, total),
        "brands": by_cat["brands"] / max(1, total),
        "features": by_cat["features"] / max(1, total),
        "pain_points": by_cat["pain_points"] / max(1, total),
        "top10_unique_share": top_unique / max(1, matched),
        # counts for CI / gates
        "total_posts": int(total),
        "matched_posts": int(matched),
        "matched_brands": int(by_cat["brands"]),
        "matched_features": int(by_cat["features"]),
        "matched_pain_points": int(by_cat["pain_points"]),
        "top10_unique_hits": int(top_unique),
    }


def _load_layer_map(path: Path | None) -> Dict[str, str]:
    default = {
        "ecommerce": "L1",
        "AmazonSeller": "L2",
        "Shopify": "L2",
        "dropship": "L3",
        "dropshipping": "L4",
    }
    if not path:
        return default
    try:
        text = path.read_text(encoding="utf-8")
        try:
            data = _json.loads(text)
        except Exception:
            import yaml  # type: ignore
            data = yaml.safe_load(text)
        out: Dict[str, str] = {}
        for k, v in (data or {}).items():
            out[str(k)] = str(v)
        return out or default
    except Exception:
        return default


def compute_layer_coverage(lexicon: Dict[str, List[Term]], corpus_glob: str, per_file_limit: int = 20, *, layer_map_path: Path | None = None) -> List[Dict[str, object]]:
    # Map filename stem to layer (configurable)
    layer_by_sub = _load_layer_map(layer_map_path)
    files = [Path(p) for p in glob.glob(corpus_glob)]
    texts_by_layer: Dict[str, List[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}
    for fp in files:
        layer = layer_by_sub.get(fp.stem)
        if not layer:
            continue
        cnt = 0
        for obj in _iter_jsonl(fp):
            t = f"{obj.get('title','')} {obj.get('selftext','')}".strip()
            if not t:
                continue
            texts_by_layer[layer].append(t)
            cnt += 1
            if cnt >= per_file_limit:
                break

    rows: List[Dict[str, object]] = []
    for layer, terms in lexicon.items():
        m = HybridMatcher(terms, enable_semantic=False)
        texts = texts_by_layer.get(layer, [])
        total = len(texts)
        hits = 0
        for txt in texts:
            if m.match_text(txt):
                hits += 1
        rows.append({"layer": layer, "posts": total, "hit_posts": hits, "coverage": round(hits / max(1, total), 4)})
    return rows


def unique_at_500(lexicon_path: Path) -> int:
    data = json.loads(lexicon_path.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    terms = []
    for cats in layers.values():
        for arr in cats.values():
            terms.extend([str(x.get("canonical", "")).lower() for x in arr])
    return len(set(terms))


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2 metrics generator")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--entity", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2.csv"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--out-prefix", default="backend/reports/local-acceptance/metrics/metrics")
    ap.add_argument("--limit-per-sub", type=int, default=20)
    ap.add_argument("--layer-map", type=Path, default=Path(os.getenv("SEMANTIC_LAYER_MAP", "")) if os.getenv("SEMANTIC_LAYER_MAP") else None)
    args = ap.parse_args()

    Path(args.out_prefix).parent.mkdir(parents=True, exist_ok=True)

    lex = _load_lexicon_v21(args.lexicon)
    layer_rows = compute_layer_coverage(lex, args.corpus, args.limit_per_sub, layer_map_path=args.layer_map)
    ent_cov = compute_entity_coverage(args.entity, args.corpus)
    uniq = unique_at_500(args.lexicon)

    # write CSV
    csv_path = Path(f"{args.out_prefix}.csv")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["unique_at_500", uniq])
        w.writerow(["entity_coverage_overall", f"{ent_cov['overall']:.4f}"])
        w.writerow(["entity_coverage_brands", f"{ent_cov['brands']:.4f}"])
        w.writerow(["entity_coverage_features", f"{ent_cov['features']:.4f}"])
        w.writerow(["entity_coverage_pain_points", f"{ent_cov['pain_points']:.4f}"])
        w.writerow(["entity_top10_unique_share", f"{ent_cov['top10_unique_share']:.4f}"])
        w.writerow(["section", "entity_counts"]) 
        w.writerow(["name", "value"]) 
        w.writerow(["total_posts", ent_cov.get("total_posts", 0)])
        w.writerow(["matched_posts", ent_cov.get("matched_posts", 0)])
        w.writerow(["top10_unique_hits", ent_cov.get("top10_unique_hits", 0)])
        w.writerow(["section", "layer_coverage"]) 
        w.writerow(["layer", "posts", "hit_posts", "coverage"]) 
        for r in layer_rows:
            w.writerow([r["layer"], r["posts"], r["hit_posts"], r["coverage"]])

    # write JSON snapshot
    json_path = Path(f"{args.out_prefix}.json")
    snap = {
        "unique_at_500": uniq,
        "entity_coverage": ent_cov,
        "layer_coverage": layer_rows,
    }
    json_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "csv": str(csv_path), "json": str(json_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
