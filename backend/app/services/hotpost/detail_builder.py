from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from app.schemas.hotpost import Hotpost
from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.hotpost.rules import count_resonance


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def compute_rant_intensity(signal_groups: Iterable[dict[str, list[str]]]) -> dict[str, float]:
    counts = Counter()
    total = 0
    for groups in signal_groups:
        if groups.get("strong"):
            counts["strong"] += 1
        elif groups.get("medium"):
            counts["medium"] += 1
        elif groups.get("weak"):
            counts["weak"] += 1
        total += 1
    if total == 0:
        return {"strong": 0.0, "medium": 0.0, "weak": 0.0}
    return {key: counts.get(key, 0) / total for key in ("strong", "medium", "weak")}


def compute_need_urgency(signal_groups: Iterable[dict[str, list[str]]]) -> dict[str, float]:
    counts = Counter()
    total = 0
    for groups in signal_groups:
        if groups.get("unmet_need"):
            counts["urgent"] += 1
        elif groups.get("seeking"):
            counts["moderate"] += 1
        else:
            counts["casual"] += 1
        total += 1
    if total == 0:
        return {"urgent": 0.0, "moderate": 0.0, "casual": 0.0}
    return {key: counts.get(key, 0) / total for key in ("urgent", "moderate", "casual")}


def build_top_rants(posts: list[Hotpost]) -> list[dict[str, Any]]:
    ranked = sorted(posts, key=lambda p: p.signal_score or 0.0, reverse=True)
    output: list[dict[str, Any]] = []
    for post in ranked[:5]:
        payload = post.model_dump()
        payload["rant_score"] = post.signal_score
        payload["rant_signals"] = post.signals
        payload["why_important"] = post.why_relevant
        output.append(payload)
    return output


def build_top_discovery_posts(posts: list[Hotpost]) -> list[dict[str, Any]]:
    lexicon = load_default_hotpost_keywords()
    ranked: list[tuple[int, Hotpost]] = []
    for post in posts:
        comments = [_as_dict(c) for c in (post.top_comments or [])]
        resonance = count_resonance(comments, lexicon)
        ranked.append((resonance, post))

    ranked.sort(key=lambda item: item[0], reverse=True)
    output: list[dict[str, Any]] = []
    for resonance, post in ranked[:5]:
        payload = post.model_dump()
        payload["resonance_count"] = resonance
        payload["why_important"] = post.why_relevant
        output.append(payload)
    return output


def extract_competitor_mentions(
    posts: list[Hotpost],
    *,
    query: str | None = None,
) -> list[dict[str, Any]]:
    flags = re.IGNORECASE
    patterns = [
        re.compile(r"([A-Z][A-Za-z0-9&+.-]{2,})\s+vs\.?\s+([A-Z][A-Za-z0-9&+.-]{2,})", flags),
        re.compile(r"\b(?:versus)\s+([A-Z][A-Za-z0-9&+.-]{2,})", flags),
        re.compile(r"\b(?:alternative to|alternatives to|switch(?:ed)? to|switched to|from|compared to|compare with)\s+([A-Z][A-Za-z0-9&+.-]{2,})", flags),
    ]
    query_lower = (query or "").lower()
    counts: Counter[str] = Counter()
    for post in posts:
        text = f"{post.title} {post.body_preview or ''}"
        for pattern in patterns:
            for match in pattern.findall(text):
                if isinstance(match, tuple):
                    names = match
                else:
                    names = (match,)
                for name in names:
                    clean = name.strip()
                    if not clean or clean.lower() in query_lower:
                        continue
                    counts[clean] += 1

    competitors: list[dict[str, Any]] = []
    for name, mentions in counts.most_common(5):
        competitors.append(
            {
                "name": name,
                "mentions": mentions,
                "sentiment": "neutral",
            }
        )
    return competitors


__all__ = [
    "compute_rant_intensity",
    "compute_need_urgency",
    "build_top_rants",
    "build_top_discovery_posts",
    "extract_competitor_mentions",
]
