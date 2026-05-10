from __future__ import annotations

import re
from typing import Optional, Any, Mapping, Sequence

from app.utils.url import normalize_reddit_url

_EN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-_/]{2,}")
_CJK_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,16}")


def _normalize_anchor(value: str) -> str:
    return str(value or "").strip().lower()


def _extract_tokens(text: str) -> set[str]:
    raw = str(text or "").lower()
    english = set(_EN_TOKEN_RE.findall(raw))
    cjk = set(_CJK_TOKEN_RE.findall(str(text or "")))
    return {token for token in english | cjk if token}


def _compose_chain_from_posts(
    posts: Sequence[Any],
    *,
    fallback_note: str,
    limit: int = 2,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for post in posts:
        payload = dict(post) if isinstance(post, Mapping) else {}
        title = str(
            payload.get("title") or payload.get("content") or payload.get("text") or ""
        ).strip()
        if not title:
            continue
        url = normalize_reddit_url(
            url=str(payload.get("url") or ""),
            permalink=str(payload.get("permalink") or ""),
        )
        note_parts = [
            str(payload.get("community") or payload.get("subreddit") or "").strip(),
            str(payload.get("note") or "").strip(),
        ]
        dedupe_key = url or title
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(
            {
                "title": title[:120],
                "url": url,
                "note": " | ".join([part for part in note_parts if part]) or fallback_note,
            }
        )
        if len(items) >= limit:
            break
    return items


def _compose_chain_from_comments(
    comments: Sequence[Any],
    *,
    anchors: Sequence[str],
    fallback_note: str,
    limit: int = 2,
) -> list[dict[str, str]]:
    anchor_tokens: set[str] = set()
    for anchor in anchors:
        anchor_tokens.update(_extract_tokens(anchor))
    if not anchor_tokens:
        return []

    scored: list[tuple[int, Mapping[str, Any]]] = []
    for comment in comments:
        if not isinstance(comment, Mapping):
            continue
        text = str(comment.get("text") or comment.get("body") or "").strip()
        if not text:
            continue
        tokens = _extract_tokens(text)
        overlap = len(anchor_tokens & tokens)
        if overlap <= 0:
            continue
        scored.append((overlap, comment))

    scored.sort(key=lambda item: item[0], reverse=True)
    return _compose_chain_from_posts(
        [payload for _, payload in scored],
        fallback_note=fallback_note,
        limit=limit,
    )


def _compose_chain_from_quotes(
    quotes: Sequence[Any],
    *,
    fallback_note: str,
    limit: int = 2,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for quote in quotes:
        title = str(quote or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        items.append({"title": title[:120], "url": "", "note": fallback_note})
        if len(items) >= limit:
            break
    return items


def build_evidence_ledger(
    *,
    insights: Mapping[str, Any],
    sample_posts_db: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    limit: int = 2,
) -> dict[str, Any]:
    pain_entries: list[dict[str, Any]] = []
    opportunity_entries: list[dict[str, Any]] = []
    pain_points = [
        row for row in (insights.get("pain_points") or []) if isinstance(row, Mapping)
    ]
    opportunities = [
        row for row in (insights.get("opportunities") or []) if isinstance(row, Mapping)
    ]

    for row in pain_points:
        anchor = str(row.get("description") or row.get("title") or "").strip()
        voices = [str(value or "").strip() for value in (row.get("user_examples") or [])]
        chain = _compose_chain_from_posts(
            row.get("example_posts") or [],
            fallback_note="Reddit 原帖",
            limit=limit,
        ) or _compose_chain_from_comments(
            sample_comments_db,
            anchors=[anchor, *voices],
            fallback_note="Reddit 评论",
            limit=limit,
        ) or _compose_chain_from_posts(
            sample_posts_db,
            fallback_note="事实样本原帖",
            limit=limit,
        ) or _compose_chain_from_quotes(
            voices,
            fallback_note="用户原话",
            limit=limit,
        )
        pain_entries.append(
            {
                "anchor": anchor,
                "normalized_anchor": _normalize_anchor(anchor),
                "evidence_chain": chain,
            }
        )

    for row in opportunities:
        anchor = str(row.get("description") or row.get("title") or "").strip()
        linked_pain = str(row.get("linked_pain_cluster") or "").strip()
        chain = _compose_chain_from_posts(
            row.get("source_examples") or [],
            fallback_note="机会证据",
            limit=limit,
        )
        if not chain and linked_pain:
            for pain_entry in pain_entries:
                if pain_entry.get("normalized_anchor") == _normalize_anchor(linked_pain):
                    chain = list(pain_entry.get("evidence_chain") or [])
                    break
        opportunity_entries.append(
            {
                "anchor": anchor,
                "normalized_anchor": _normalize_anchor(anchor),
                "linked_pain": linked_pain,
                "normalized_linked_pain": _normalize_anchor(linked_pain),
                "evidence_chain": chain[:limit],
            }
        )

    return {
        "pain_points": pain_entries,
        "opportunities": opportunity_entries,
    }


def lookup_evidence_chain(
    ledger:Optional[ Mapping[str, Any]],
    *,
    section: str,
    anchor: str = "",
    linked_pain: str = "",
) -> list[dict[str, str]]:
    if not isinstance(ledger, Mapping):
        return []
    items = ledger.get(section)
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return []

    normalized_anchor = _normalize_anchor(anchor)
    normalized_linked_pain = _normalize_anchor(linked_pain)

    for item in items:
        if not isinstance(item, Mapping):
            continue
        if normalized_anchor and item.get("normalized_anchor") == normalized_anchor:
            return list(item.get("evidence_chain") or [])

    if section == "opportunities" and normalized_linked_pain:
        for item in items:
            if not isinstance(item, Mapping):
                continue
            if item.get("normalized_linked_pain") == normalized_linked_pain:
                return list(item.get("evidence_chain") or [])
    return []


__all__ = ["build_evidence_ledger", "lookup_evidence_chain"]
