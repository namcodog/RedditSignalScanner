from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Sequence

from app.services.analysis.search_query import clean_search_term

_ASCII_ENTITY_RE = re.compile(r"[A-Za-z][A-Za-z0-9._/+:-]{1,40}")
_GENERIC_ENTITY_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "what",
    "when",
    "where",
    "which",
    "this",
    "that",
    "from",
    "into",
}


@dataclass(frozen=True, slots=True)
class OpenQuestionQueryPlan:
    intent: str
    must_keep: tuple[str, ...]
    must_not_invent: tuple[str, ...]
    route_query_en: str
    retrieve_queries_en: tuple[str, ...]
    rerank_query: str
    route_keywords: tuple[str, ...]
    retrieve_keywords: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _dedupe(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = str(raw or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _extract_must_keep(description: str) -> tuple[str, ...]:
    found: list[str] = []
    for match in _ASCII_ENTITY_RE.finditer(description or ""):
        token = match.group(0).strip()
        lower = token.lower()
        if len(token) < 2 or lower in _GENERIC_ENTITY_STOPWORDS:
            continue
        found.append(token)
    return tuple(_dedupe(found))


def _english_keywords(keywords: Sequence[str], must_keep: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    for raw in [*must_keep, *keywords]:
        cleaned = clean_search_term(str(raw or ""))
        if not cleaned:
            continue
        ordered.append(cleaned)
    return _dedupe(ordered)


def _build_retrieve_queries(tokens: Sequence[str]) -> tuple[str, ...]:
    if not tokens:
        return ()
    variants = (
        " ".join(tokens[:3]).strip(),
        " ".join(tokens[1:4]).strip() if len(tokens) > 3 else " ".join(tokens[:2]).strip(),
        " ".join(tokens[:2]).strip(),
    )
    return tuple(_dedupe([item for item in variants if item]))


def build_open_question_query_plan(
    *,
    description: str,
    keywords: Sequence[str],
) -> OpenQuestionQueryPlan:
    must_keep = _extract_must_keep(description)
    english_keywords = _english_keywords(keywords, must_keep)
    route_keywords = tuple(english_keywords[:8])
    retrieve_keywords = tuple(english_keywords[:12])
    route_query_en = " ".join(route_keywords[:4]).strip()
    retrieve_queries_en = _build_retrieve_queries(retrieve_keywords)
    return OpenQuestionQueryPlan(
        intent="open_topic",
        must_keep=must_keep,
        must_not_invent=(),
        route_query_en=route_query_en,
        retrieve_queries_en=retrieve_queries_en,
        rerank_query=str(description or "").strip(),
        route_keywords=route_keywords,
        retrieve_keywords=retrieve_keywords,
    )


__all__ = ["OpenQuestionQueryPlan", "build_open_question_query_plan"]
