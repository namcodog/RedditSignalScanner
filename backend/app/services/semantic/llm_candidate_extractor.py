from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping

from sqlalchemy import text as sqltext
from sqlalchemy.ext.asyncio import AsyncSession


_TERM_CLEAN_RE = re.compile(r"[\\s\\-_/]+")
_URL_RE = re.compile(r"https?://\\S+|www\\.\\S+")
_DIGIT_RE = re.compile(r"\\d")
_STOPWORDS = {
    "help",
    "issue",
    "problem",
    "question",
    "advice",
    "need",
    "looking",
    "thanks",
}


@dataclass
class LlmCandidateStats:
    term: str
    frequency: int = 0
    max_confidence: float = 0.0
    subreddits: set[str] = field(default_factory=set)
    authors: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)


def _normalize_term(raw: Any) -> str | None:
    if not raw:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    if _URL_RE.search(text):
        return None
    text = _TERM_CLEAN_RE.sub(" ", text).strip()
    if len(text) < 2 or len(text) > 64:
        return None
    if text in _STOPWORDS:
        return None
    if _DIGIT_RE.search(text) and len(text) < 4:
        return None
    return text


def _safe_json(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, Mapping):
                return parsed
        except Exception:
            return {}
    return {}


def _extract_terms(analysis: Mapping[str, Any]) -> Dict[str, List[str]]:
    pain_tags = analysis.get("pain_tags") or []
    aspect_tags = analysis.get("aspect_tags") or []
    entities = analysis.get("entities") or {}
    entity_new = entities.get("new") or []

    return {
        "pain_point": list(pain_tags) if isinstance(pain_tags, list) else [],
        "feature": list(aspect_tags) if isinstance(aspect_tags, list) else [],
        "brand": list(entity_new) if isinstance(entity_new, list) else [],
    }


def _confidence_from_score(value_score: Any) -> float:
    try:
        raw = float(value_score or 0.0)
    except Exception:
        raw = 0.0
    return max(0.0, min(1.0, raw / 10.0))


async def extract_llm_candidates(
    *,
    session: AsyncSession,
    lookback_days: int,
    post_limit: int,
    comment_limit: int,
    existing_terms: Iterable[str],
) -> Dict[str, LlmCandidateStats]:
    stats: Dict[str, LlmCandidateStats] = {}
    existing = {t.strip().lower() for t in existing_terms if t}

    def _accumulate(
        *,
        analysis_raw: Any,
        value_score: Any,
        subreddit: Any,
        author: Any,
    ) -> None:
        analysis = _safe_json(analysis_raw)
        conf = _confidence_from_score(value_score)
        terms_by_cat = _extract_terms(analysis)
        for category, terms in terms_by_cat.items():
            for raw in terms:
                term = _normalize_term(raw)
                if not term or term in existing:
                    continue
                record = stats.get(term)
                if record is None:
                    record = LlmCandidateStats(term=term)
                    stats[term] = record
                record.frequency += 1
                record.max_confidence = max(record.max_confidence, conf)
                if subreddit:
                    record.subreddits.add(str(subreddit).strip().lower())
                if author:
                    record.authors.add(str(author).strip().lower())
                record.categories.add(category)

    post_rows = await session.execute(
        sqltext(
            """
            SELECT l.tags_analysis, l.value_score, p.subreddit, p.author_name
            FROM post_llm_labels l
            JOIN posts_raw p ON p.id = l.post_id
            WHERE l.created_at >= now() - (:days * interval '1 day')
              AND l.business_pool IN ('core','lab')
            ORDER BY l.created_at DESC
            LIMIT :limit
            """
        ),
        {"days": int(lookback_days), "limit": int(post_limit)},
    )
    for row in post_rows.mappings().all():
        _accumulate(
            analysis_raw=row.get("tags_analysis"),
            value_score=row.get("value_score"),
            subreddit=row.get("subreddit"),
            author=row.get("author_name"),
        )

    comment_rows = await session.execute(
        sqltext(
            """
            SELECT l.tags_analysis, l.value_score, c.subreddit, c.author_name
            FROM comment_llm_labels l
            JOIN comments c ON c.id = l.comment_id
            WHERE l.created_at >= now() - (:days * interval '1 day')
              AND l.business_pool IN ('core','lab')
            ORDER BY l.created_at DESC
            LIMIT :limit
            """
        ),
        {"days": int(lookback_days), "limit": int(comment_limit)},
    )
    for row in comment_rows.mappings().all():
        _accumulate(
            analysis_raw=row.get("tags_analysis"),
            value_score=row.get("value_score"),
            subreddit=row.get("subreddit"),
            author=row.get("author_name"),
        )

    return stats
