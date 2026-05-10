from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Any, Mapping


_COMMENTS_PATH_RE = re.compile(r"/comments/(?P<post_id>[a-z0-9]+)/", re.IGNORECASE)
_REMOVED_BODIES = {"[deleted]", "[removed]", "deleted", "removed"}


def extract_reddit_post_id(source_link: str) ->Optional[ str]:
    candidate = str(source_link or "").strip()
    if not candidate:
        return None
    if not candidate.endswith("/"):
        candidate = f"{candidate}/"
    match = _COMMENTS_PATH_RE.search(candidate)
    if not match:
        return None
    return str(match.group("post_id")).lower()


async def collect_hot_comment_sample(
    card: Mapping[str, Any],
    *,
    reddit_client: Any,
    limit: int = 40,
    depth: int = 2,
    comment_timeout: float = 15.0,
) -> dict[str, Any]:
    sampled_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post_id = extract_reddit_post_id(str(card.get("source_link") or ""))
    if not post_id:
        return {
            "post_id": None,
            "sample_comments": [],
            "sample_size": 0,
            "sampled_at": sampled_at,
            "fetch_status": "invalid_source_link",
        }

    try:
        comments = await reddit_client.fetch_post_comments(
            post_id,
            mode="smart_shallow",
            limit=limit,
            depth=depth,
            comment_timeout=comment_timeout,
        )
    except Exception:
        return {
            "post_id": post_id,
            "sample_comments": [],
            "sample_size": 0,
            "sampled_at": sampled_at,
            "fetch_status": "fetch_failed",
        }

    sample_comments = _select_effective_comments(comments, limit=limit)
    return {
        "post_id": post_id,
        "sample_comments": sample_comments,
        "sample_size": len(sample_comments),
        "sampled_at": sampled_at,
        "fetch_status": "ok",
    }


def _select_effective_comments(comments: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_bodies: set[str] = set()
    for item in comments:
        text = _clean_comment_text(item.get("body"))
        if not text:
            continue
        dedupe_key = _dedupe_key(text)
        if dedupe_key in seen_bodies:
            continue
        seen_bodies.add(dedupe_key)
        selected.append(
            {
                "body": text,
                "score": int(item.get("score") or 0),
                "author": str(item.get("author") or ""),
                "created_utc": item.get("created_utc"),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _clean_comment_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in _REMOVED_BODIES:
        return ""
    if len(text) < 12:
        return ""
    return text


def _dedupe_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


__all__ = ["collect_hot_comment_sample", "extract_reddit_post_id"]
