#!/usr/bin/env python3
from __future__ import annotations

"""
Build L1 semantic baseline (Spec 011) from an ecommerce‑centric corpus.

Design goals:
- Offline friendly: fall back to HashingVectorizer when Sentence‑Transformers
  is unavailable.
- Deterministic and fast for small corpora (tests feed ~10–20 docs).

Outputs:
- Pickle file containing: terms (List[str]), embeddings (np.ndarray) and meta.

CLI:
  python backend/scripts/build_L1_baseline.py \
    --corpus backend/data/reddit_corpus/ecommerce.jsonl \
    --output backend/config/semantic_sets/L1_baseline_embeddings.pkl \
    [--model sentence-transformers/all-MiniLM-L6-v2]
"""

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, HashingVectorizer


@dataclass
class Baseline:
    terms: List[str]
    embeddings: np.ndarray
    meta: dict


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


def _load_texts(corpus: Path) -> list[str]:
    texts: list[str] = []
    if corpus.is_dir():
        for p in corpus.glob("*.jsonl"):
            texts.extend(_load_texts(p))
        return texts
    for obj in _iter_jsonl(corpus):
        title = str(obj.get("title", ""))
        body = str(obj.get("selftext", ""))
        s = f"{title} {body}".strip()
        if s:
            texts.append(s)
    return texts


def _extract_terms(texts: list[str], *, max_features: int = 256) -> list[str]:
    if not texts:
        return []
    # 小样本容错：不足两条文本时降级 min_df=1
    min_df = 1 if len(texts) < 2 else 2
    try:
        tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=max_features, min_df=min_df, stop_words="english")
        X = tfidf.fit_transform(texts)
        feats = list(tfidf.get_feature_names_out())
        if not feats:
            return []
        scores = np.asarray(X.sum(axis=0)).ravel()
        order = np.argsort(-scores)
        return [feats[i] for i in order]
    except ValueError:
        return []


def _embed_terms(terms: list[str], *, model_name: str | None, dim: int = 128) -> tuple[np.ndarray, dict]:
    if not terms:
        return np.zeros((0, dim), dtype=np.float32), {"method": "hashing", "dim": dim}
    # 优先 ST，失败回退 HashingVectorizer（字符 3-5gram）
    if model_name:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            model = SentenceTransformer(model_name)
            emb = np.asarray(model.encode(terms, normalize_embeddings=True), dtype=np.float32)
            return emb, {"method": f"st::{model_name}", "dim": int(emb.shape[1])}
        except Exception:
            pass
    hv = HashingVectorizer(analyzer="char", ngram_range=(3, 5), n_features=dim, alternate_sign=False)
    X = hv.transform(terms)
    return X.toarray().astype(np.float32), {"method": "hashing", "dim": dim}


def build_baseline(corpus: Path, out_pkl: Path, *, model_name: str | None = None, max_features: int = 256) -> Baseline:
    texts = _load_texts(corpus)
    terms = _extract_terms(texts, max_features=max_features)
    emb, meta = _embed_terms(terms, model_name=model_name)
    baseline = Baseline(terms=terms, embeddings=emb, meta=meta)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(baseline, f)
    return baseline


def main() -> None:  # pragma: no cover - thin CLI
    ap = argparse.ArgumentParser(description="Build L1 semantic baseline")
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    build_baseline(args.corpus, args.output, model_name=args.model)
    print(f"✅ Wrote L1 baseline to {args.output}")


if __name__ == "__main__":
    main()
