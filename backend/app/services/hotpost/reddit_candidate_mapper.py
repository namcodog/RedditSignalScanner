from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_clues import QuotePreview
from app.schemas.hotpost_signal import WhyNowReason
from app.schemas.hotpost_source_scopes import RedditSearchSpec
from app.services.hotpost.growth_pack_intake import (
    is_growth_pack_title_blocked,
    match_growth_pack_keywords,
    resolve_growth_pack_signal_level,
    uses_growth_pack_intake_path,
)
from app.services.infrastructure.reddit_client import RedditPost
from app.services.hotpost.source_scope_catalog import get_source_scope


_SWITCH_WORDS = ("switch", "replace", "alternative", "migrate", "move from")
_RECOMMEND_WORDS = ("recommend", "looking for", "best", "any tool", "need help")
_PAIN_WORDS = ("problem", "issue", "bug", "pain", "stuck", "hate", "broken")
_LOW_VALUE_COMMENT_NEEDLES = (
    "i am a bot",
    "auto moderator",
    "automoderator",
    "contact the moderators",
    "scam warning",
    "reddit is filled with scams",
)


def build_candidate_pack(
    spec: RedditSearchSpec, post: RedditPost, comments: list[dict], *, collect_batch_id: str, collected_at: datetime
) ->Optional[ CandidatePack]:
    matched_keywords = list(spec.matched_keywords)
    primary_reason = spec.primary_reason
    query = spec.query or f"listing:{spec.sort}:{spec.time_filter}"

    if uses_growth_pack_intake_path(spec.source_scope_id, spec.topic_pack_id) and spec.mode == "listing":
        if is_growth_pack_title_blocked(post.title):
            return None
        matched_keywords = match_growth_pack_keywords(spec.topic_pack_id or "", post.title, post.selftext)
        if not matched_keywords:
            return None
        signal_level = resolve_growth_pack_signal_level(post)
        primary_reason = f"{spec.topic_pack_id}:listing_keyword_bridge"
        query = matched_keywords[0]
    else:
        signal_level = _resolve_signal_level(post)
    if signal_level is None:
        return None
    scope = get_source_scope(spec.source_scope_id)
    quotes = [_comment_quote(post, item) for item in comments if _usable_comment(item)]
    return CandidatePack(
        candidate_id=f"cand-{spec.source_scope_id}-{post.id}",
        signal_id=f"sig-{post.id}",
        source_scope_id=spec.source_scope_id,
        source_scope_name=scope.title,
        topic_pack_id=spec.topic_pack_id,
        topic_cluster_id=spec.topic_cluster_id,
        topic_cluster_ids=spec.topic_cluster_ids,
        named_topic_ids=spec.named_topic_ids,
        query=query,
        matched_subreddit=post.subreddit,
        post_id=post.id,
        title=post.title,
        score=post.score,
        num_comments=post.num_comments,
        created_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
        collected_at=collected_at,
        collect_batch_id=collect_batch_id,
        time_window=_resolve_time_window(spec),
        signal_level=signal_level,
        why_now_reason=_resolve_why_now(spec, post),
        listing_source=spec.listing_source,
        primary_reason=primary_reason,
        matched_keywords=matched_keywords,
        top_communities=[f"r/{post.subreddit}"],
        thread_count=1,
        community_count=1,
        quote_count=len(quotes),
        intent_tags=_resolve_intents(spec, post),
        evidence_quotes=quotes[:2],
    )


def _resolve_signal_level(post: RedditPost) ->Optional[ str]:
    age_hours = (datetime.now(timezone.utc).timestamp() - post.created_utc) / 3600
    if age_hours <= 72 and (post.score >= 500 or post.num_comments >= 60):
        return "hot"
    if age_hours <= 24 * 7 and (post.score >= 100 or post.num_comments >= 30):
        return "rising"
    if age_hours <= 24 * 30 and (post.score >= 30 or post.num_comments >= 10):
        return "sustained"
    return None


def _resolve_time_window(spec: RedditSearchSpec) -> str:
    return "24h" if spec.time_filter == "day" else "7d"


def _resolve_why_now(spec: RedditSearchSpec, post: RedditPost) -> WhyNowReason:
    age_hours = (datetime.now(timezone.utc).timestamp() - post.created_utc) / 3600
    if age_hours <= 24:
        return "new_threads_24h"
    haystack = f"{spec.query or ''} {post.title} {post.selftext}".lower()
    if any(word in haystack for word in _SWITCH_WORDS + _RECOMMEND_WORDS):
        return "switch_signal_7d"
    return "recurring_7d"


def _resolve_intents(spec: RedditSearchSpec, post: RedditPost) -> list[str]:
    haystack = f"{spec.query or ''} {post.title} {post.selftext}".lower()
    tags: list[str] = []
    if any(word in haystack for word in _SWITCH_WORDS):
        tags.append("替换")
    if any(word in haystack for word in _RECOMMEND_WORDS):
        tags.append("求推荐")
    if any(word in haystack for word in _PAIN_WORDS):
        tags.append("避坑")
    return tags or ["趋势变化"]


def _usable_comment(comment: dict) -> bool:
    body = str(comment.get("body") or "").strip()
    lowered = body.lower()
    return (
        len(body) >= 20
        and not body.startswith("[removed]")
        and not any(needle in lowered for needle in _LOW_VALUE_COMMENT_NEEDLES)
    )


def _comment_quote(post: RedditPost, comment: dict) -> QuotePreview:
    permalink = str(comment.get("permalink") or post.permalink or "")
    return QuotePreview(
        text=str(comment.get("body") or "").strip(),
        community=f"r/{post.subreddit}",
        permalink=f"https://www.reddit.com{permalink}",
    )
