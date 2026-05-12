#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import pickle
from pathlib import Path
import re
from typing import Any

import numpy as np


_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*")
_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "plus",
    "that",
    "the",
    "this",
    "with",
}


@dataclass
class Baseline:
    terms: list[str]
    embeddings: np.ndarray
    meta: dict[str, Any]


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                yield value


def _load_texts(corpus: Path) -> list[str]:
    if corpus.is_dir():
        texts: list[str] = []
        for path in sorted(corpus.glob("*.jsonl")):
            texts.extend(_load_texts(path))
        return texts

    texts = []
    for row in _iter_jsonl(corpus):
        title = str(row.get("title") or "")
        body = str(row.get("selftext") or "")
        text = f"{title} {body}".strip()
        if text:
            texts.append(text)
    return texts


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    ]


def _extract_terms(texts: list[str], *, max_features: int) -> list[str]:
    counts: Counter[str] = Counter()
    for text in texts:
        tokens = _tokens(text)
        counts.update(tokens)
        counts.update(
            f"{left} {right}"
            for left, right in zip(tokens, tokens[1:])
            if left != right
        )

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [term for term, _count in ranked[:max_features]]


def _hash_embeddings(terms: list[str], *, dim: int = 128) -> np.ndarray:
    embeddings = np.zeros((len(terms), dim), dtype=np.float32)
    for row, term in enumerate(terms):
        tokens = term.split() or [term]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dim
            embeddings[row, index] += 1.0
        norm = float(np.linalg.norm(embeddings[row]))
        if norm:
            embeddings[row] /= norm
    return embeddings


def build_baseline(
    corpus: Path,
    out_pkl: Path,
    *,
    model_name: str | None = None,
    max_features: int = 256,
) -> Baseline:
    texts = _load_texts(corpus)
    terms = _extract_terms(texts, max_features=max_features)
    embeddings = _hash_embeddings(terms)
    baseline = Baseline(
        terms=terms,
        embeddings=embeddings,
        meta={
            "method": "hashing",
            "dim": int(embeddings.shape[1]) if embeddings.size else 128,
            "model_name": model_name,
            "documents": len(texts),
        },
    )

    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as handle:
        pickle.dump(baseline, handle)
    return baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Build L1 semantic baseline")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()

    build_baseline(args.corpus, args.output, model_name=args.model)
    print(f"Wrote L1 baseline to {args.output}")


if __name__ == "__main__":
    main()
