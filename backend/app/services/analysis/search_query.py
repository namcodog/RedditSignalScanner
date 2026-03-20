from __future__ import annotations

import re
from typing import Sequence

_QUERY_TOKEN_SPLIT_RE = re.compile(r"\s+")
_QUERY_TOKEN_CLEAN_RE = re.compile(r"[^a-z0-9_+\- ]+")


def clean_search_term(term: str) -> str:
    cleaned = _QUERY_TOKEN_CLEAN_RE.sub(" ", term.strip().lower())
    pieces = [piece for piece in _QUERY_TOKEN_SPLIT_RE.split(cleaned) if piece]
    return " ".join(pieces)


def build_websearch_query(tokens: Sequence[str]) -> str | None:
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens or []:
        cleaned = clean_search_term(str(token))
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(f"\"{cleaned}\"" if " " in cleaned else cleaned)
    if not terms:
        return None
    return " OR ".join(terms)


__all__ = ["build_websearch_query", "clean_search_term"]
