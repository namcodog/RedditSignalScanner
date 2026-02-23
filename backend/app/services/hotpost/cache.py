from __future__ import annotations

import hashlib
import os
from typing import Iterable

from app.services.hotpost.repository import normalize_query
from app.utils.subreddit import normalize_subreddit_name


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def build_hotpost_cache_key(
    query: str,
    mode: str,
    subreddits: Iterable[str] | None,
) -> str:
    normalized_query = normalize_query(query)
    subs: list[str] = []
    for raw in subreddits or []:
        name = normalize_subreddit_name(str(raw))
        if name:
            subs.append(name)
    subs = sorted(set(subs))
    query_hash = _hash_text(normalized_query)
    subs_hash = _hash_text(",".join(subs))
    return f"reddit_hot:{mode}:{query_hash}:{subs_hash}"


def get_hotpost_cache_ttl_seconds(mode: str) -> int:
    if mode == "trending":
        return int(os.getenv("CACHE_TTL_TRENDING", "1800"))
    if mode == "rant":
        return int(os.getenv("CACHE_TTL_RANT", "7200"))
    if mode == "opportunity":
        return int(os.getenv("CACHE_TTL_OPPORTUNITY", "3600"))
    return int(os.getenv("CACHE_TTL_DEFAULT", "3600"))


__all__ = ["build_hotpost_cache_key", "get_hotpost_cache_ttl_seconds"]
