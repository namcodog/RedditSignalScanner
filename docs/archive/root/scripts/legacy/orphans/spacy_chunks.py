#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Set, Tuple

import spacy  # type: ignore

from scripts.stopwords_utils import load_stopwords


def iter_jsonl(path: Path) -> Iterable[dict]:
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


def normalize(text: str) -> str:
    text = re.sub(r"https?://\\S+", " ", text)
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def is_noise(
    phrase: str,
    token_stops: Set[str],
    phrase_stops: Set[str],
    regex_stops: List[re.Pattern[str]],
    keep_tokens: Set[str],
) -> bool:
    low = phrase.lower().strip()
    if len(low) < 4 or len(low) > 30:
        return True
    if low in phrase_stops:
        return True
    for pat in regex_stops:
        if pat.search(low):
            return True
    toks = re.split(r"\\s+|[-/]+", low)
    # keep tokens override
    if any(tok in keep_tokens for tok in toks):
        return False
    # if all tokens are stops -> noise
    if all(tok in token_stops for tok in toks):
        return True
    # if any token is stop and no keep tokens -> consider noise
    if any(tok in token_stops for tok in toks):
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Extract noun chunks/NER phrases with spaCy.")
    ap.add_argument("--corpus", required=True, help="Path to JSONL with title/selftext fields")
    ap.add_argument("--stopwords-dir", required=True, help="Directory with stopwords files")
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--top-k", type=int, default=100)
    args = ap.parse_args()

    token_stops, phrase_stops, reddit_stops, ecommerce_tokens, regex_stops, keep_tokens = load_stopwords(
        Path(args.stopwords_dir)
    )
    # merge stops
    token_stops = token_stops.union(reddit_stops).union(ecommerce_tokens)

    nlp = spacy.load("en_core_web_sm")
    ctr = Counter()
    total = 0
    for obj in iter_jsonl(Path(args.corpus)):
        txt = f"{obj.get('title','')} {obj.get('selftext','')}"
        txt = normalize(txt)
        if not txt:
            continue
        total += 1
        doc = nlp(txt)
        # noun chunks
        for chunk in doc.noun_chunks:
            ph = chunk.text.strip()
            if is_noise(ph, token_stops, phrase_stops, regex_stops, keep_tokens):
                continue
            ctr[ph.lower()] += 1
        # NER ORG/PRODUCT
        for ent in doc.ents:
            if ent.label_ in {"ORG", "PRODUCT"}:
                ph = ent.text.strip()
                if is_noise(ph, token_stops, phrase_stops, regex_stops, keep_tokens):
                    continue
                ctr[ph.lower()] += 1

    # write csv
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    top = ctr.most_common(args.top_k)
    with out.open("w", encoding="utf-8") as f:
        f.write("term,freq\\n")
        for term, freq in top:
            if freq < args.min_freq:
                continue
            f.write(f"{term},{freq}\\n")

    print(json.dumps({"input": total, "unique": len(ctr), "top_saved": len(top), "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
