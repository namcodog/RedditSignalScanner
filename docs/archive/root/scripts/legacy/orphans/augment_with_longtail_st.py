#!/usr/bin/env python3
from __future__ import annotations

"""
Stage 2 - Long-tail augmentation using Sentence-Transformers.

Goal: reduce entity top10_unique_share by adding multi-word long-tail
feature phrases that match posts NOT already covered by current top10 terms,
and are semantically distinct from the current head (top10) terms.

Inputs:
  --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv
  --candidates backend/reports/local-acceptance/crossborder_candidates.csv
  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl"
  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv

Key params:
  --model sentence-transformers/all-MiniLM-L6-v2
  --sim-max 0.50 (max similarity to any top10 term; lower -> more diverse)
  --replace-n 16 (how many features to replace)
  --max-brands 30, --min-pains 42, --total 100

Heuristics:
  - Only consider candidate category=features and phrases (contains space/-/ /)
  - Filter with semantic similarity to top10 head terms (<= sim-max)
  - Score candidates by number of posts they match outside the union of current top10 hits
  - Replace the last N features in current dict with top-N candidates
  - Keep constraints: brands <= 30; pain_points >= min-pains; total=100
"""

import argparse
import csv
import glob
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set

import numpy as np


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _is_phrase(s: str) -> bool:
    return (" " in s) or ("-" in s) or ("/" in s)


def _make_pat(t: str):
    esc = re.escape(t.strip())
    return re.compile(rf"(?i)\b{esc}\b")


def load_dict(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def load_candidates(path: Path) -> List[Tuple[str, str, str, int, float]]:
    out: List[Tuple[str, str, str, int, float]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get("canonical") or "").strip()
            cat = (row.get("category") or "features").strip()
            lay = (row.get("layer") or "L2").strip()
            try:
                freq = int(row.get("freq") or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            out.append((can, cat, lay, freq, score))
    # prefer higher freq first, then score
    out.sort(key=lambda x: (-x[3], -x[4]))
    return out


def compute_top10_union(rows: List[Dict[str, str]], corpus_glob: str) -> Tuple[Set[str], List[Tuple[str, int]]]:
    # count hits per term
    patterns: List[Tuple[re.Pattern, str]] = []
    for r in rows:
        term = (r.get("canonical") or "").strip()
        if not term:
            continue
        patterns.append((_make_pat(term), term))
    hits: Dict[str, int] = {}
    files = [Path(p) for p in glob.glob(corpus_glob)]
    for fp in files:
        for obj in _iter_jsonl(fp):
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            for pat, term in patterns:
                if pat.search(text):
                    hits[term] = hits.get(term, 0) + 1
    top = sorted(hits.items(), key=lambda x: -x[1])[:10]
    # union set of post ids matched by top10
    top_terms = {t for t, _ in top}
    top_pats = [(_make_pat(t), t) for t in top_terms]
    union_ids: Set[str] = set()
    for fp in files:
        for obj in _iter_jsonl(fp):
            pid = str(obj.get("id", ""))
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            if any(p.search(text) for p, _ in top_pats):
                union_ids.add(pid)
    return union_ids, top


def _cos_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_n = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_n = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return np.clip(a_n @ b_n.T, -1.0, 1.0)


STOP_PHRASE_SUBSTR = {
    "days ago", "weekly", "welcome", "hours", "question", "newbie", "discussion",
    "2024", "2025", "years", "months", "weeks", "days",
}


def select_longtail_with_st(model_name: str, sim_max: float, top_terms: List[str], cands: List[Tuple[str, str, str, int, float]]) -> List[Tuple[str, str, int, float]]:
    """Return list of (canonical, layer, freq, score) filtered by semantic distance to top_terms."""
    from sentence_transformers import SentenceTransformer  # type: ignore

    model = SentenceTransformer(model_name)
    # Embed top terms and candidate phrases
    head_texts = [t for t in top_terms]
    head_emb = model.encode(head_texts, normalize_embeddings=True, convert_to_numpy=True)

    phrases: List[str] = []
    meta: List[Tuple[str, int, float, str]] = []  # (layer, freq, score, canonical)
    for can, cat, lay, freq, score in cands:
        if cat != "features":
            continue
        if not _is_phrase(can):
            continue
        low = can.lower()
        if any(s in low for s in STOP_PHRASE_SUBSTR):
            continue
        phrases.append(can)
        meta.append((lay, int(freq), float(score), can))

    if not phrases:
        return []

    ph_emb = model.encode(phrases, normalize_embeddings=True, convert_to_numpy=True)
    sims = _cos_sim(ph_emb, head_emb)  # shape: (num_phrases, num_heads)
    max_sims = sims.max(axis=1) if sims.size else np.array([])

    picked: List[Tuple[str, str, int, float]] = []
    for i, ms in enumerate(max_sims):
        if ms <= sim_max:
            lay, freq, score, can = meta[i]
            picked.append((can, lay, freq, score))
    # Rank by freq desc then score desc
    picked.sort(key=lambda x: (-x[2], -x[3]))
    return picked


def score_outside_top_union(cands: List[Tuple[str, str, int, float]], top10_union: Set[str], corpus_glob: str) -> List[Tuple[str, str, float, int]]:
    files = [Path(p) for p in glob.glob(corpus_glob)]
    scored: List[Tuple[str, str, float, int]] = []
    for can, lay, freq, score in cands:
        pat = _make_pat(can)
        new_hits = 0
        for fp in files:
            for obj in _iter_jsonl(fp):
                pid = str(obj.get("id", ""))
                if pid in top10_union:
                    continue
                text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
                if pat.search(text):
                    new_hits += 1
        if new_hits > 0:
            scored.append((can, lay, float(new_hits), int(freq)))
    scored.sort(key=lambda x: (-x[2], -x[3]))
    return scored


def hits_per_term(rows: List[Dict[str, str]], corpus_glob: str) -> Dict[str, Set[str]]:
    """Return mapping term -> set(post_ids) that match the term."""
    pats: List[Tuple[re.Pattern, str]] = []
    for r in rows:
        term = (r.get("canonical") or "").strip()
        if not term:
            continue
        pats.append((_make_pat(term), term))
    files = [Path(p) for p in glob.glob(corpus_glob)]
    per: Dict[str, Set[str]] = {}
    for fp in files:
        for obj in _iter_jsonl(fp):
            pid = str(obj.get("id", ""))
            text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
            for pat, term in pats:
                if pat.search(text):
                    s = per.setdefault(term, set())
                    s.add(pid)
    return per


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["canonical", "category", "source_layer", "weight", "norm_weight", "polarity"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def main() -> int:
    ap = argparse.ArgumentParser(description="Augment entity dict with ST-based long-tail phrases")
    ap.add_argument("--dict", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2_diverse.csv"))
    ap.add_argument("--candidates", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates.csv"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--output", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2_diverse.csv"))
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--sim-max", type=float, default=0.50)
    ap.add_argument("--replace-n", type=int, default=16)
    ap.add_argument("--max-brands", type=int, default=30)
    ap.add_argument("--min-pains", type=int, default=42)
    ap.add_argument("--total", type=int, default=100)
    # MMR diversification weights
    ap.add_argument("--alpha", type=float, default=1.0, help="weight for normalized new coverage")
    ap.add_argument("--beta", type=float, default=0.4, help="penalty for similarity to head (top10)")
    ap.add_argument("--gamma", type=float, default=0.3, help="penalty for similarity to already selected")
    ap.add_argument("--delta", type=float, default=0.2, help="penalty for overlap with already selected posts")
    # Cluster quota to avoid near-duplicates across candidates
    ap.add_argument("--cluster-k", type=int, default=0, help="KMeans clusters on candidate embeddings; 0 to disable")
    ap.add_argument("--cluster-quota", type=int, default=0, help="max selections per cluster; 0 to disable")
    ap.add_argument("--min-tail-ratio", type=float, default=0.6, help="min ratio of hits outside top10 union to total hits")
    args = ap.parse_args()

    rows = load_dict(args.dict)
    existing_lc = {(r.get("canonical") or "").strip().lower() for r in rows}
    top_union, top_pairs = compute_top10_union(rows, args.corpus)
    top_terms_sorted = [t for (t, c) in sorted(top_pairs, key=lambda x: -x[1])]

    cands = load_candidates(args.candidates)
    st_picked = select_longtail_with_st(args.model, args.sim_max, top_terms_sorted, cands)

    # Build embeddings and head similarities for MMR scoring
    from sentence_transformers import SentenceTransformer  # type: ignore
    st_model = SentenceTransformer(args.model)
    cand_texts = [c[0] for c in st_picked]
    cand_emb = st_model.encode(cand_texts, normalize_embeddings=True, convert_to_numpy=True) if cand_texts else np.zeros((0, 384))
    head_texts = top_terms_sorted
    head_emb = st_model.encode(head_texts, normalize_embeddings=True, convert_to_numpy=True) if head_texts else np.zeros((0, 384))
    head_sims = _cos_sim(cand_emb, head_emb) if (len(cand_emb) and len(head_emb)) else np.zeros((len(cand_emb), 0))
    max_head_sim = head_sims.max(axis=1) if head_sims.size else np.zeros((len(cand_emb),))

    # Optional: KMeans cluster-quota on candidates
    cluster_labels: List[int] = []
    cluster_used: Dict[int, int] = {}
    if args.cluster_k and args.cluster_k > 0 and len(cand_emb) >= args.cluster_k:
        try:
            from sklearn.cluster import KMeans  # type: ignore
            km = KMeans(n_clusters=args.cluster_k, random_state=42, n_init=10)
            labs = km.fit_predict(cand_emb)
            cluster_labels = list(map(int, labs))
            cluster_used = {i: 0 for i in range(args.cluster_k)}
        except Exception:
            cluster_labels = []

    # Precompute matched post ids for each candidate
    files = [Path(p) for p in glob.glob(args.corpus)]
    cand_post_ids: List[Set[str]] = []
    cand_patterns = [ _make_pat(txt) for txt in cand_texts ]
    for pat in cand_patterns:
        ids: Set[str] = set()
        for fp in files:
            for obj in _iter_jsonl(fp):
                pid = str(obj.get("id", ""))
                text = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
                if pat.search(text):
                    ids.add(pid)
        cand_post_ids.append(ids)
    # Tail-ratio filter relative to top10 union
    tail_keep: List[bool] = []
    for ids in cand_post_ids:
        if not ids:
            tail_keep.append(False)
            continue
        tail_hits = len(ids - top_union)
        tail_ratio = tail_hits / max(1, len(ids))
        tail_keep.append(tail_ratio >= max(0.0, min(1.0, args.min_tail_ratio)))

    # partition existing
    brands = [r for r in rows if (r.get("category") or "").strip() == "brands"][: args.max_brands]
    pains = [r for r in rows if (r.get("category") or "").strip() == "pain_points"]
    feats = [r for r in rows if (r.get("category") or "").strip() == "features"]

    # choose features to replace: prefer those contributing little outside top10 union
    term_hits = hits_per_term(rows, args.corpus)
    top_term_set = {t for t, _ in top_pairs}
    # compute outside-hit score per feature term
    outside_score: List[Tuple[int, str]] = []  # (outside_hits, term)
    for f in feats:
        t = (f.get("canonical") or "").strip()
        # protect top10 terms from replacement (complement instead of replacing heads)
        if t in top_term_set:
            continue
        s = term_hits.get(t, set())
        outs = len([pid for pid in s if pid not in top_union])
        outside_score.append((outs, t))
    # pick the lowest outside contributors
    outside_score.sort(key=lambda x: (x[0], x[1]))
    n = min(args.replace_n, len(feats))
    to_replace_terms = {t for _, t in outside_score[:n]}
    keep_feats = [f for f in feats if (f.get("canonical") or "").strip() not in to_replace_terms]

    add_feats: List[Dict[str, str]] = []
    added_lc: Set[str] = set()
    selected_embs: List[np.ndarray] = []
    selected_posts: Set[str] = set()
    covered_posts: Set[str] = set(top_union)
    available = [i for i in range(len(st_picked)) if (i < len(tail_keep) and tail_keep[i])]
    while len(add_feats) < n and available:
        # normalization factor for new coverage in this round
        new_cov_vals: List[int] = []
        for j in available:
            new_cov_vals.append(len(cand_post_ids[j] - covered_posts))
        max_new_cov = max(new_cov_vals) if new_cov_vals else 1
        if max_new_cov <= 0:
            break
        best = None  # (score, idx)
        for j in list(available):
            can, lay, freq, sc = st_picked[j]
            low = (can or "").lower()
            if low in existing_lc or low in added_lc:
                available.remove(j)
                continue
            # enforce cluster quota if enabled
            if cluster_labels:
                cid = cluster_labels[j]
                if args.cluster_quota and args.cluster_quota > 0 and cluster_used.get(cid, 0) >= args.cluster_quota:
                    # skip candidates from saturated cluster
                    available.remove(j)
                    continue
            posts = cand_post_ids[j]
            new_cov = len(posts - covered_posts)
            if new_cov <= 0:
                available.remove(j)
                continue
            new_cov_norm = new_cov / max_new_cov
            # head sim
            hsim = float(max_head_sim[j]) if j < len(max_head_sim) else 0.0
            # sim to selected
            if selected_embs:
                sel_mat = np.vstack(selected_embs)
                sim_sel = _cos_sim(cand_emb[j:j+1, :], sel_mat).max()  # type: ignore
            else:
                sim_sel = 0.0
            # overlap with already selected posts
            overlap = len(posts & selected_posts) / max(1, len(posts))
            score = args.alpha * new_cov_norm - args.beta * hsim - args.gamma * float(sim_sel) - args.delta * overlap
            if (best is None) or (score > best[0]):
                best = (score, j)
        if best is None:
            break
        _, j = best
        can, lay, freq, sc = st_picked[j]
        add_feats.append({
            "canonical": can,
            "category": "features",
            "source_layer": lay,
            "weight": "1.00",
            "norm_weight": "1.00",
            "polarity": "neutral",
        })
        added_lc.add((can or "").lower())
        selected_embs.append(cand_emb[j:j+1, :])
        selected_posts |= cand_post_ids[j]
        covered_posts |= cand_post_ids[j]
        if cluster_labels:
            cid = cluster_labels[j]
            cluster_used[cid] = cluster_used.get(cid, 0) + 1
        available.remove(j)

    merged = brands + pains + keep_feats + add_feats
    # enforce total size
    if len(merged) > args.total:
        merged = merged[: args.total]
    # ensure pains minimum by trimming features if necessary (safety)
    pains_cnt = sum(1 for r in merged if (r.get("category") or "") == "pain_points")
    if pains_cnt < args.min_pains:
        # pull back some original pain terms from rows (append before features)
        extra_pains = [r for r in rows if (r.get("category") or "") == "pain_points"][pains_cnt: args.min_pains]
        merged = brands + extra_pains + keep_feats + add_feats
        if len(merged) > args.total:
            merged = merged[: args.total]

    write_csv(merged, args.output)

    print(json.dumps({
        "status": "ok",
        "top10_terms": top_pairs,
        "added_longtail": [x["canonical"] for x in add_feats],
        "output": str(args.output),
        "replace_n": n,
        "sim_max": args.sim_max,
        "model": args.model,
        "alpha": args.alpha,
        "beta": args.beta,
        "gamma": args.gamma,
        "delta": args.delta,
        "cluster_k": args.cluster_k,
        "cluster_quota": args.cluster_quota,
        "min_tail_ratio": args.min_tail_ratio,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
