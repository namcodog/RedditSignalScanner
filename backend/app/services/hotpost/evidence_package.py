from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Callable

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.evidence_focus import (
    HotpostEvidenceFocusContext,
    build_focus_terms,
    build_query_terms,
    extract_key_quote,
    has_domain_anchor,
    is_noise_comment,
    score_comment,
    score_post,
)
from app.services.hotpost.hotpost_config import HotpostEvidencePackagingConfig


@dataclass(slots=True, frozen=True)
class HotpostEvidencePackage:
    posts_data: list[dict[str, Any]]
    comments_data: list[dict[str, Any]]


def _env_int(getenv: Callable[[str, str], str], key: str, default: int) -> int:
    try:
        return max(1, int(getenv(key, str(default))))
    except Exception:
        return default


def _trim_text(value:Optional[ str], *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def build_hotpost_evidence_package(
    *,
    mode: str,
    query: str,
    posts: list[Hotpost],
    comments: list[HotpostComment],
    positive_intent_terms: list[str],
    domain_terms: list[str],
    packaging_config: HotpostEvidencePackagingConfig,
    getenv: Callable[[str, str], str],
) -> HotpostEvidencePackage:
    # 证据打包只负责“喂对料”，不负责补结论。
    rules = packaging_config.mode_rules.get(mode)
    context = HotpostEvidenceFocusContext(
        query_terms=build_query_terms(query),
        intent_terms=positive_intent_terms,
        domain_terms=domain_terms,
        focus_terms_limit=packaging_config.focus_terms_limit,
    )
    post_limit = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_MAX_POSTS", 6 if mode in {"rant", "opportunity"} else 10)
    comment_limit = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_MAX_COMMENTS", 8 if mode == "rant" else 12)
    post_body_max_chars = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_POST_BODY_MAX_CHARS", 220 if mode == "rant" else 260)
    post_quote_max_chars = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_POST_QUOTE_MAX_CHARS", 180 if mode == "rant" else 220)
    post_quote_min_chars = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_POST_QUOTE_MIN_CHARS", 48 if mode == "rant" else 1)
    comment_max_chars = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_COMMENT_MAX_CHARS", 180 if mode == "rant" else 240)
    comment_min_chars = _env_int(getenv, f"HOTPOST_{mode.upper()}_REPORT_COMMENT_MIN_CHARS", 48 if mode == "rant" else (24 if mode == "opportunity" else 1))

    ranked_posts = sorted(posts, key=lambda post: score_post(post, context=context, rules=rules), reverse=True)
    if rules is not None:
        focused_posts = [post for post in ranked_posts if score_post(post, context=context, rules=rules)[0] >= rules.min_post_score]
        if focused_posts:
            ranked_posts = focused_posts
        if rules.keep_focus_only:
            anchored_posts = [
                post for post in ranked_posts if has_domain_anchor(context=context, text_blobs=[post.title, post.body_preview, post.subreddit])
            ]
            if anchored_posts:
                ranked_posts = anchored_posts

    posts_data = [
        {
            "id": post.id,
            "title": _trim_text(post.title, max_chars=packaging_config.title_max_chars),
            "body_preview": _trim_text(post.body_preview, max_chars=post_body_max_chars),
            "key_quote": extract_key_quote(post, trim_text=_trim_text, max_chars=post_quote_max_chars, min_chars=post_quote_min_chars),
            "score": post.score,
            "comments": post.num_comments,
            "subreddit": post.subreddit,
            "url": post.reddit_url,
            "heat_score": post.heat_score,
            "created_utc": post.created_utc,
            "signals": post.signals,
            "why_relevant": _trim_text(post.why_relevant, max_chars=packaging_config.why_relevant_max_chars) if post.why_relevant else None,
            "focus_terms": build_focus_terms(context=context, text_blobs=[post.title, post.body_preview, post.subreddit, post.why_relevant]),
        }
        for post in ranked_posts[:post_limit]
    ]

    ranked_comments = sorted(
        (item for item in comments if not is_noise_comment(item, min_chars=comment_min_chars)),
        key=lambda comment: score_comment(comment, context=context, rules=rules),
        reverse=True,
    )
    if rules is not None:
        focused_comments = [item for item in ranked_comments if score_comment(item, context=context, rules=rules)[0] >= rules.min_comment_score]
        if focused_comments:
            ranked_comments = focused_comments
        if rules.keep_focus_only:
            anchored_comments = [item for item in ranked_comments if has_domain_anchor(context=context, text_blobs=[item.body])]
            if anchored_comments:
                ranked_comments = anchored_comments

    comments_data: list[dict[str, Any]] = []
    seen: set[str] = set()
    for comment in ranked_comments:
        body = _trim_text(comment.body, max_chars=comment_max_chars)
        if not body or body.lower() in seen:
            continue
        seen.add(body.lower())
        comments_data.append(
            {
                "body": body,
                "score": comment.score,
                "permalink": comment.permalink,
                "focus_terms": build_focus_terms(context=context, text_blobs=[comment.body]),
            }
        )
        if len(comments_data) >= comment_limit:
            break

    return HotpostEvidencePackage(posts_data=posts_data, comments_data=comments_data)


__all__ = ["HotpostEvidencePackage", "build_hotpost_evidence_package"]
