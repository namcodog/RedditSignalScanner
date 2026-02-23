#!/usr/bin/env python3
from __future__ import annotations

"""
Stage 2 - Candidate term extractor.

From local corpus, propose candidate phrases per layer that are NOT already
in the semantic_sets. Uses TF-IDF with 1–3 grams and optionally KeyBERT
if available. Applies filters:
- min frequency
- stopwords & URL/noise removal
- negative/positive triggers for pain points

Outputs YAML-like JSON (yml suffix) + CSV for quick review.
"""

import argparse
import csv
import glob
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import re

try:
    import spacy  # type: ignore
    _HAS_SPACY = True
except Exception:
    spacy = None  # type: ignore
    _HAS_SPACY = False

from scripts.stopwords_utils import load_stopwords


NEGATIVE_TOKENS = {
    "issue", "issues", "problem", "problems", "refund", "refunds", "chargeback", "chargebacks",
    "suspend", "suspension", "ban", "banned", "blocked", "violation", "risk", "fraud", "loss",
    "complaint", "complaints", "delay", "late", "stuck", "decline", "error", "wrong", "bad",
    "worst", "terrible", "awful", "horrible", "nightmare", "disaster", "defect", "defective",
    "missing", "broken", "failed", "failure", "abandoned", "saturated",
}

STOP_EXTRA = {"ve", "re", "ll", "amp", "www", "http", "https", "com", "t", "m", "co"}


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


def _load_texts_by_layer(corpus_glob: str) -> Dict[str, List[str]]:
    layer_by_sub = {
        "ecommerce": "L1",
        "AmazonSeller": "L2",
        "Shopify": "L2",
        "dropship": "L3",
        "dropshipping": "L4",
    }
    texts: Dict[str, List[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}
    for fp in [Path(p) for p in glob.glob(corpus_glob)]:
        layer = layer_by_sub.get(fp.stem)
        if not layer:
            continue
        for obj in _iter_jsonl(fp):
            t = f"{obj.get('title','')} {obj.get('selftext','')}".strip()
            if t:
                texts[layer].append(t)
    return texts


def _existing_terms(lex_path: Path) -> Set[str]:
    text = lex_path.read_text(encoding="utf-8")
    s: Set[str] = set()
    try:
        data = json.loads(text)
        for cats in (data.get("layers") or {}).values():
            for arr in cats.values():
                for it in arr:
                    t = str(it.get("canonical", "")).lower()
                    if t:
                        s.add(t)
    except Exception:
        # YAML fallback
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        layers = data.get("layers")
        themes = data.get("themes")
        if layers:
            for cats in layers.values():
                for arr in cats.values():
                    for it in arr:
                        if isinstance(it, str):
                            t = it
                        else:
                            t = str(it.get("canonical", ""))
                        if t:
                            s.add(t.lower())
        elif themes:
            for cfg in themes.values():
                for arr in cfg.values():
                    if isinstance(arr, list):
                        for it in arr:
                            if isinstance(it, str):
                                s.add(it.lower())
                            elif isinstance(it, dict):
                                t = str(it.get("canonical", ""))
                                if t:
                                    s.add(t.lower())
    return s


def _tfidf_candidates(texts: List[str], *, max_features: int = 1500) -> List[Tuple[str, float, int]]:
    if not texts:
        return []
    min_df = 2 if len(texts) >= 2 else 1
    try:
        tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=max_features, min_df=min_df, stop_words='english')
        X = tfidf.fit_transform(texts)
        feats = list(tfidf.get_feature_names_out())
        scores = np.asarray(X.sum(axis=0)).ravel()
    except Exception:
        return []
    try:
        cnt = CountVectorizer(ngram_range=(1, 3), vocabulary=feats, stop_words='english')
        C = cnt.fit_transform(texts)
        freqs = np.asarray(C.sum(axis=0)).ravel()
    except Exception:
        return []
    order = np.argsort(-scores)
    return [(feats[i], float(scores[i]), int(freqs[i])) for i in order]


def _is_noise(term: str, *, token_stops: Set[str], phrase_stops: Set[str], regex_stops: List[re.Pattern[str]]) -> bool:
    t = term.strip().lower()
    if len(t) < 3:
        return True
    if t in STOP_EXTRA or t in token_stops:
        return True
    # 短语停用词：精确或子串命中均视为噪声
    if t in phrase_stops or any(p in t for p in phrase_stops):
        return True
    if t.startswith("http") or ".com" in t:
        return True
    # 任一子词命中停用词也视为噪声
    for tok in re.split(r"\s+|[-/]+", t):
        if tok in token_stops or tok in STOP_EXTRA:
            return True
    for pat in regex_stops:
        if pat.search(t):
            return True
    return False


def _category_guess(term: str) -> str:
    low = term.lower()
    if any(neg in low for neg in NEGATIVE_TOKENS):
        return "pain_points"
    # 默认特征
    return "features"


def extract_candidates(lex_path: Path, corpus_glob: str, *, per_layer: int, min_freq: int, stopwords_dir: Path, use_pos: bool) -> Dict[str, Dict[str, List[dict]]]:
    existing = _existing_terms(lex_path)
    texts = _load_texts_by_layer(corpus_glob)
    out: Dict[str, Dict[str, List[dict]]] = {k: {"features": [], "pain_points": []} for k in ["L1", "L2", "L3", "L4"]}

    token_stops, phrase_stops, reddit_stops, ecommerce_tokens, regex_stops, keep_tokens = load_stopwords(stopwords_dir)

    nlp = None
    if use_pos and _HAS_SPACY:
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            nlp = spacy.blank("en")

    def _pos_ok(t: str) -> bool:
        if not use_pos:
            return True
        if nlp is None:
            return True
        doc = nlp(t)
        # 允许名词/专有名词/名词短语
        if any(tok.pos_ in {"NOUN", "PROPN"} for tok in doc):
            return True
        # 含空格视为短语，放行（避免过严）
        return (" " in t or "-" in t)

    for layer, arr in texts.items():
        cands = _tfidf_candidates(arr, max_features=max(2000, per_layer * 10))
        picked: List[dict] = []
        for t, score, freq in cands:
            tl = t.lower()
            if freq < min_freq:
                continue
            if tl in existing:
                continue
            if _is_noise(t, token_stops=token_stops.union(reddit_stops), phrase_stops=phrase_stops, regex_stops=regex_stops):
                continue
            # 领域通用词在候选阶段强过滤（包含在短语子词中也过滤）
            toks = re.split(r"\s+|[-/]+", tl)
            if any(tok in ecommerce_tokens for tok in toks) and tl not in keep_tokens:
                continue
            # 客套/求助类直接过滤（候选阶段）
            if any(x in tl for x in ("appreciate", "thanks", "thankyou", "pls", "please")):
                continue
            if not _pos_ok(t):
                continue
            cat = _category_guess(t)
            picked.append({
                "canonical": t,
                "category": cat,
                "layer": layer,
                "score": round(score, 2),
                "freq": int(freq),
            })
            if len(picked) >= per_layer:
                break
        for p in picked:
            out[layer][p["category"]].append(p)
    return out


def _write_outputs(obj: dict, out_yml: Path, out_csv: Path) -> None:
    out_yml.parent.mkdir(parents=True, exist_ok=True)
    out_yml.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical", "category", "layer", "freq", "score"])
        for layer, cats in obj.items():
            for cat, arr in cats.items():
                for it in arr:
                    w.writerow([it["canonical"], cat, layer, it["freq"], it["score"]])


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract candidate terms per layer")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    ap.add_argument("--out-yml", type=Path, default=Path("backend/config/semantic_sets/crossborder_candidates.yml"))
    ap.add_argument("--out-csv", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates.csv"))
    ap.add_argument("--per-layer", type=int, default=50)
    ap.add_argument("--min-freq", type=int, default=8)
    ap.add_argument("--stopwords-dir", type=Path, default=Path("backend/config/nlp/stopwords"))
    ap.add_argument("--use-pos", type=int, default=1)
    args = ap.parse_args()

    obj = extract_candidates(
        args.lexicon,
        args.corpus,
        per_layer=args.per_layer,
        min_freq=args.min_freq,
        stopwords_dir=args.stopwords_dir,
        use_pos=bool(args.use_pos),
    )
    _write_outputs(obj, args.out_yml, args.out_csv)
    print(json.dumps({"status": "ok", "per_layer": args.per_layer, "out": str(args.out_csv)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
