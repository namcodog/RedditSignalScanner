from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Any

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.hotpost_config import HotpostEvidencePackagingModeConfig


@dataclass(slots=True, frozen=True)
class HotpostEvidenceFocusContext:
    query_terms: list[str]
    intent_terms: list[str]
    domain_terms: list[str]
    focus_terms_limit: int


def build_query_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    return [token for token in tokens if len(token) >= 4][:6]


def matched_terms(text:Optional[ str], terms: list[str]) -> list[str]:
    haystack = str(text or "").lower()
    return [term for term in terms if term and term in haystack]


def build_focus_terms(*, context: HotpostEvidenceFocusContext, text_blobs:Optional[ list[str]]) -> list[str]:
    hits: list[str] = []
    for term_group in (context.query_terms, context.intent_terms, context.domain_terms):
        for term in term_group:
            if any(term in str(blob or "").lower() for blob in text_blobs) and term not in hits:
                hits.append(term)
            if len(hits) >= context.focus_terms_limit:
                return hits
    return hits


def has_domain_anchor(*, context: HotpostEvidenceFocusContext, text_blobs:Optional[ list[str]]) -> bool:
    if context.domain_terms:
        combined = " ".join(str(blob or "") for blob in text_blobs)
        return bool(matched_terms(combined, context.domain_terms))
    return bool(build_focus_terms(context=context, text_blobs=text_blobs[:1]))


def _comment_value(comment: Any, field: str) -> Any:
    if isinstance(comment, dict):
        return comment.get(field)
    return getattr(comment, field, None)


def is_noise_comment(comment: Any, *, min_chars: int) -> bool:
    author = str(_comment_value(comment, "author") or "").strip().lower()
    body = " ".join(str(_comment_value(comment, "body") or "").split())
    body_lower = body.lower()
    if not body or len(body) < min_chars:
        return True
    if any(
        phrase in body_lower
        for phrase in (
            "friendly reminder",
            "question and answer subreddit",
            "rules listed in the sidebar",
            "automatically performed",
        )
    ):
        return True
    return author in {"automoderator", "mod", "moderator"}


def extract_key_quote_from_comments(
    comments: list[Any],
    *,
    trim_text: Any,
    max_chars: int,
    min_chars: int,
) ->Optional[ str]:
    for comment in comments:
        if is_noise_comment(comment, min_chars=min_chars):
            continue
        body = trim_text(_comment_value(comment, "body"), max_chars=max_chars)
        if body:
            return body
    return None


def score_post(
    post: Hotpost,
    *,
    context: HotpostEvidenceFocusContext,
    rules:Optional[ HotpostEvidencePackagingModeConfig],
) -> tuple[float, float, int, int]:
    title = str(post.title or "")
    body = str(post.body_preview or "")
    subreddit = str(post.subreddit or "")
    why_relevant = str(post.why_relevant or "")
    query_hits = len(matched_terms(f"{title} {body} {subreddit}", context.query_terms))
    intent_hits = len(matched_terms(f"{title} {body}", context.intent_terms))
    domain_hits = len(matched_terms(f"{title} {body} {subreddit}", context.domain_terms))
    why_hits = len(
        matched_terms(
            why_relevant,
            context.query_terms + context.intent_terms + context.domain_terms,
        )
    )
    score = float(query_hits)
    if rules is not None:
        score = (
            query_hits * rules.query_weight
            + intent_hits * rules.intent_weight
            + domain_hits * rules.domain_weight
            + why_hits * rules.why_relevant_weight
        )
    return (score, float(post.signal_score or 0.0), int(post.heat_score or 0), int(post.num_comments or 0))


def score_comment(
    comment: HotpostComment,
    *,
    context: HotpostEvidenceFocusContext,
    rules:Optional[ HotpostEvidencePackagingModeConfig],
) -> tuple[float, int, int]:
    query_hits = len(matched_terms(comment.body, context.query_terms))
    intent_hits = len(matched_terms(comment.body, context.intent_terms))
    domain_hits = len(matched_terms(comment.body, context.domain_terms))
    score = float(query_hits)
    if rules is not None:
        score = (
            query_hits * rules.query_weight
            + intent_hits * rules.intent_weight
            + domain_hits * rules.domain_weight
        )
    return (score, int(comment.score or 0), len(str(comment.body or "")))


def extract_key_quote(
    post: Hotpost,
    *,
    trim_text: Any,
    max_chars: int,
    min_chars: int,
) ->Optional[ str]:
    return extract_key_quote_from_comments(
        post.top_comments,
        trim_text=trim_text,
        max_chars=max_chars,
        min_chars=min_chars,
    )


__all__ = [
    "HotpostEvidenceFocusContext",
    "build_focus_terms",
    "build_query_terms",
    "extract_key_quote",
    "extract_key_quote_from_comments",
    "has_domain_anchor",
    "is_noise_comment",
    "matched_terms",
    "score_comment",
    "score_post",
]
