from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from app.services.hotpost.compare_thread_context import (
    resolve_compare_side_entries,
    resolve_focus_match,
)
from app.services.hotpost.evidence_focus import is_noise_comment
from app.services.hotpost.rant_evidence_helpers import (
    get_payload_value,
)
from app.services.hotpost.rules import normalize_text


def _post_voice_candidates(post: Any) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    title = str(get_payload_value(post, "title") or "").strip()
    body_preview = str(get_payload_value(post, "body_preview") or "").strip()
    if title:
        candidates.append(("post_title", title))
    if body_preview and normalize_text(body_preview) != normalize_text(title):
        candidates.append(("post_body", body_preview))
    return candidates


def iter_compare_evidence_entries(
    *,
    payload: dict[str, Any],
    compare_targets: list[str],
    focus_terms: list[str],
    complaint_detector: Callable[[str], bool],
) -> Iterator[dict[str, Any]]:
    for post in list(payload.get("top_posts") or []):
        thread_title = str(get_payload_value(post, "title") or "").strip()
        thread_body = str(get_payload_value(post, "body_preview") or "").strip()
        for comment in list(getattr(post, "top_comments", None) or []):
            quote = str(getattr(comment, "body", "") or "").strip()
            if not quote or is_noise_comment(comment, min_chars=24):
                continue
            focus_hit, focus_resolution_source = resolve_focus_match(
                quote=quote,
                focus_terms=focus_terms,
                thread_title=thread_title,
                thread_body=thread_body,
            )
            if not focus_hit:
                continue
            for resolved in resolve_compare_side_entries(
                quote=quote,
                compare_targets=compare_targets,
                complaint_detector=complaint_detector,
                thread_title=thread_title,
                thread_body=thread_body,
            ):
                yield {
                    "quote_text": quote,
                    "url": getattr(comment, "permalink", None) or getattr(post, "reddit_url", None),
                    "thread_key": getattr(post, "id", None) or getattr(post, "reddit_url", None),
                    "quote_id": getattr(comment, "comment_fullname", None),
                    "subreddit": getattr(post, "subreddit", None),
                    "created_utc": getattr(post, "created_utc", None),
                    "score": getattr(comment, "score", None),
                    "source": "comment_evidence",
                    "source_type": "comment",
                    "side": resolved["side"],
                    "stance": resolved["stance"],
                    "side_resolution_source": resolved["side_resolution_source"],
                    "focus_resolution_source": focus_resolution_source,
                    "confidence": resolved["confidence"],
                    "force_valid": True,
                }

    for quote_item in list(payload.get("top_quotes") or []):
        quote = str(get_payload_value(quote_item, "quote") or "").strip()
        focus_hit, focus_resolution_source = resolve_focus_match(
            quote=quote,
            focus_terms=focus_terms,
        )
        if not quote or not focus_hit:
            continue
        for resolved in resolve_compare_side_entries(
            quote=quote,
            compare_targets=compare_targets,
            complaint_detector=complaint_detector,
        ):
            yield {
                "quote_text": quote,
                "url": get_payload_value(quote_item, "url") or get_payload_value(quote_item, "thread_url"),
                "thread_key": (
                    get_payload_value(quote_item, "thread_id")
                    or get_payload_value(quote_item, "thread_url")
                    or get_payload_value(quote_item, "url")
                    or quote
                ),
                "quote_id": get_payload_value(quote_item, "quote_id"),
                "subreddit": get_payload_value(quote_item, "subreddit"),
                "created_utc": get_payload_value(quote_item, "created_utc"),
                "score": get_payload_value(quote_item, "score"),
                "source": "top_quote",
                "source_type": "quote",
                "side": resolved["side"],
                "stance": resolved["stance"],
                "side_resolution_source": resolved["side_resolution_source"],
                "focus_resolution_source": focus_resolution_source,
                "confidence": resolved["confidence"],
                "force_valid": True,
            }

    for post in list(payload.get("top_posts") or []):
        for source_name, quote in _post_voice_candidates(post):
            focus_hit, focus_resolution_source = resolve_focus_match(
                quote=quote,
                focus_terms=focus_terms,
            )
            if not focus_hit:
                continue
            for resolved in resolve_compare_side_entries(
                quote=quote,
                compare_targets=compare_targets,
                complaint_detector=complaint_detector,
            ):
                yield {
                    "quote_text": quote,
                    "url": get_payload_value(post, "reddit_url"),
                    "thread_key": get_payload_value(post, "id") or get_payload_value(post, "reddit_url") or quote,
                    "quote_id": f"post:{get_payload_value(post, 'id') or ''}:{source_name}",
                    "subreddit": get_payload_value(post, "subreddit"),
                    "created_utc": get_payload_value(post, "created_utc"),
                    "score": get_payload_value(post, "score"),
                    "source": source_name,
                    "source_type": "post",
                    "side": resolved["side"],
                    "stance": resolved["stance"],
                    "side_resolution_source": resolved["side_resolution_source"],
                    "focus_resolution_source": focus_resolution_source,
                    "confidence": resolved["confidence"],
                    "force_valid": True,
                }


__all__ = ["iter_compare_evidence_entries"]
