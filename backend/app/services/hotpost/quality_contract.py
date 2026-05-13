from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Optional, Any

from app.schemas.hotpost import Hotpost
from app.services.hotpost.evidence_focus import extract_key_quote_from_comments
from app.services.hotpost.hotpost_config import load_default_hotpost_runtime_config
from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.hotpost.rules import (
    classify_pain_category,
    classify_rant_friction_category,
    normalize_pain_category_label,
)


_DEFAULT_LEXICON = load_default_hotpost_keywords()
_RANT_FRICTION_CATEGORIES = {
    "trust_gap",
    "weak_buy_reason",
    "wrong_audience",
    "identity_friction",
    "transaction_friction",
}
_QUERY_KEYWORD_STOP_TERMS = {
    "issue",
    "issues",
    "problem",
    "problems",
    "complaint",
    "complaints",
    "frustrated",
    "frustrating",
    "hate",
    "hates",
    "bad",
    "worse",
    "worst",
    "people",
    "lately",
    "today",
    "now",
}
_QUOTE_COMPLAINT_MARKERS = (
    "annoying",
    "bug",
    "bugs",
    "broken",
    "broke",
    "can't",
    "cannot",
    "confusing",
    "confused",
    "crash",
    "crashes",
    "crashing",
    "drop",
    "drops",
    "dropping",
    "error",
    "expensive",
    "fails",
    "failing",
    "freeze",
    "freezes",
    "freezing",
    "fluff",
    "frustrat",
    "garbage",
    "go nuts",
    "ignore",
    "ignores",
    "ignored",
    "lag",
    "lagging",
    "miss",
    "misses",
    "missing",
    "nonsense",
    "not worth",
    "out of sync",
    "rewrite",
    "rewriting",
    "slow",
    "stuck",
    "too expensive",
    "unreliable",
    "unusable",
    "useless",
    "worse",
    "worst",
    "崩",
    "很差",
    "空话",
    "胡扯",
    "难用",
)
_QUOTE_COMPARE_PREFERENCE_MARKERS = (
    "better than",
    "compared to",
    "follows the whole brief",
    "keeps the full brief",
    "more than",
    "prefer",
    "understands",
    "understand instructions",
    "worse than",
    "不如",
    "更能",
    "更好",
)
_QUOTE_ADVICE_MARKERS = (
    "check that",
    "consider ",
    "disable ",
    "double-check",
    "i recommend",
    "make sure",
    "reseat",
    "try ",
    "use render",
    "you have to",
    "you should",
)
_QUOTE_SOLUTION_TITLE_HINTS = (
    "how i fixed",
    "i fixed",
    "my fix",
    "fix that worked",
    "solved this",
    "solved it",
    "workaround that fixed",
)


@dataclass(frozen=True, slots=True)
class HotpostQualityContractResult:
    payload: dict[str, Any]
    gaps: list[str]
    notes: list[str]
def _to_text(value: Any) -> str:
    return str(value or "").strip()

def _post_field(post: Any, field: str) -> Any:
    if hasattr(post, field):
        return getattr(post, field)
    if isinstance(post, dict):
        return post.get(field)
    if hasattr(post, "model_dump"):
        return post.model_dump().get(field)
    return None

def _first_post_quote(post: Any) ->Optional[ str]:
    top_comments = _post_field(post, "top_comments") or []
    if not isinstance(top_comments, list):
        return None
    return extract_key_quote_from_comments(
        top_comments,
        trim_text=lambda value, *, max_chars: _to_text(value)[:max_chars],
        max_chars=180,
        min_chars=48,
    )

def _quote_is_noise(text: str) -> bool:
    lowered = _to_text(text).lower()
    if len(lowered) < 20:
        return True
    if any(
        phrase in lowered
        for phrase in (
            "friendly reminder",
            "question and answer subreddit",
            "rules listed in the sidebar",
            "interested",
            "same here",
            "join our discord",
            "discord.gg/",
            "i am a bot",
            "performed automatically",
            "contact the moderators",
        )
    ):
        return True
    advice_hits = sum(1 for marker in _QUOTE_ADVICE_MARKERS if marker in lowered)
    if advice_hits >= 2 and not _quote_has_explicit_voice(lowered):
        return True
    return False

def _quote_url(post: Any, comment:Optional[ Any] = None) ->Optional[ str]:
    permalink = _to_text(_post_field(comment, "permalink")) if comment is not None else ""
    if permalink.startswith("/"):
        return f"https://www.reddit.com{permalink}"
    return _to_text(_post_field(post, "reddit_url")) or None


def _quote_thread_url(post: Any) ->Optional[ str]:
    return _to_text(_post_field(post, "reddit_url")) or None


def _quote_thread_id(post: Any) ->Optional[ str]:
    return _to_text(_post_field(post, "id")) or None


def _quote_id(post: Any, comment:Optional[ Any] = None) ->Optional[ str]:
    post_id = _quote_thread_id(post)
    if comment is not None:
        comment_id = _to_text(_post_field(comment, "comment_fullname")) or _to_text(_post_field(comment, "permalink"))
        if post_id and comment_id:
            return f"{post_id}:{comment_id}"
        return comment_id or post_id or None
    if post_id:
        return f"{post_id}:title"
    return _quote_thread_url(post)


def _quote_has_explicit_voice(text: str) -> bool:
    lowered = _to_text(text).lower()
    if not lowered:
        return False
    if any(marker in lowered for marker in _QUOTE_COMPLAINT_MARKERS):
        return True
    if any(marker in lowered for marker in _QUOTE_COMPARE_PREFERENCE_MARKERS):
        return True
    if re.search(r"\bi (?:hate|prefer|like|keep|am|was|can't|cannot)\b", lowered):
        return True
    return False


def _looks_like_solution_title(text: str) -> bool:
    lowered = _to_text(text).lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in _QUOTE_SOLUTION_TITLE_HINTS)


def _quote_quality(entry: dict[str, Any]) -> tuple[int, int, int, int]:
    quote = _to_text(entry.get("quote"))
    lowered = quote.lower()
    advice_hits = sum(1 for marker in _QUOTE_ADVICE_MARKERS if marker in lowered)
    explicit_voice = 2 if _quote_has_explicit_voice(lowered) else 1
    return (
        explicit_voice,
        max(0, 3 - min(advice_hits, 3)),
        int(entry.get("score") or 0),
        min(len(quote), 180),
    )


def _quote_why_is_generic(text: Any) -> bool:
    lowered = _to_text(text).lower()
    if not lowered:
        return True
    generic_markers = (
        "值得关注",
        "说明这个问题",
        "说明问题存在",
        "反映了用户",
        "说明用户",
        "讨论很多",
        "抱怨很多",
        "评论活跃",
        "讨论活跃",
        "继续观察",
    )
    return any(marker in lowered for marker in generic_markers)


def _build_rant_quote_why_important(quote: str) ->Optional[ str]:
    lowered = _to_text(quote).lower()
    if any(term in lowered for term in ("scam", "misleading", "lied", "does not have", "doesn't have", "support told me", "they told me")):
        return "这句原话点明的不是普通失望，而是用户觉得自己被误导了。只要这种感觉出现，后面再多功能点也很难补回信任。"
    if any(term in lowered for term in ("underwhelming", "disappointed", "waste of money", "not worth it", "isn’t going to produce", "isn't going to produce", "too weak")):
        return "这句原话暴露的是预期和实际体验之间的落差。用户不是完全不要，而是买完后觉得没有值回原本期待。"
    if any(term in lowered for term in ("maintenance", "low-maintenance", "cleaning", "mess", "hassle", "what am i doing wrong", "learning curve")):
        return "这句原话说明用户卡住的不只是结果好不好，而是整个使用和维护过程比想象中更麻烦，门槛太高。"
    if "pay to play" in lowered or "gmv max" in lowered:
        return "这句原话不是在抱怨流量少，而是在担心平台最后会逼着商家持续买量，转化会越来越依赖付费。"
    has_loss = any(
        term in lowered
        for term in (
            "no sales",
            "no sale",
            "no conversions",
            "low conversion",
            "nobody buys",
            "dead",
            "not converting",
        )
    )
    has_traffic = any(term in lowered for term in ("traffic", "views", "view", "organic", "reach"))
    has_paid = any(term in lowered for term in ("advertising", "ads", "paid", "gmv max", "pay to play"))
    if has_loss and has_traffic:
        return "这句原话把问题钉在成交层: 有流量不等于能成交，不是单纯曝光起伏。"
    if has_paid and "organic" in lowered:
        return "这句原话直接比较了自然流量带来的出单和付费投放，说明卖家怀疑广告并没有带来对应成交。"
    if has_paid and has_loss:
        return "这句原话说明大家担心的是投钱后也不成交，问题不在有没有投放，而在转化值不值。"
    if has_loss:
        return "这句原话直接说到卖不动，说明问题已经影响成交，不只是一般抱怨。"
    return None


def _quote_duplicate_index(merged: list[dict[str, Any]], quote: str, *, url: str) ->Optional[ int]:
    normalized_quote = _to_text(quote).casefold()
    normalized_url = _to_text(url)
    if not normalized_quote:
        return None
    for idx, existing in enumerate(merged):
        existing_quote = _to_text(existing.get("quote")).casefold()
        if not existing_quote:
            continue
        if existing_quote == normalized_quote:
            return idx
        existing_url = _to_text(existing.get("url"))
        if not normalized_url or existing_url != normalized_url:
            continue
        shorter, longer = sorted((existing_quote, normalized_quote), key=len)
        if len(shorter) >= 48 and shorter in longer:
            return idx
    return None


def _quote_matches_text(quote: str, candidate: Any) -> bool:
    normalized_quote = _to_text(quote).casefold()
    normalized_candidate = _to_text(candidate).casefold()
    if not normalized_quote or not normalized_candidate:
        return False
    if normalized_quote == normalized_candidate:
        return True
    shorter, longer = sorted((normalized_quote, normalized_candidate), key=len)
    return len(shorter) >= 24 and shorter in longer


def _infer_quote_context(entry: dict[str, Any], top_posts: list[Hotpost]) -> dict[str, Any]:
    quote = _to_text(entry.get("quote"))
    if not quote:
        return {}
    for post in top_posts:
        if _quote_matches_text(quote, _post_field(post, "title")):
            return {
                "subreddit": _post_field(post, "subreddit"),
                "url": _quote_url(post),
                "thread_url": _quote_thread_url(post),
                "thread_id": _quote_thread_id(post),
                "quote_id": _quote_id(post),
                "created_utc": _post_field(post, "created_utc"),
            }
        for comment in (_post_field(post, "top_comments") or []):
            if _quote_matches_text(quote, _post_field(comment, "body")):
                return {
                    "subreddit": _post_field(post, "subreddit"),
                    "url": _quote_url(post, comment),
                    "thread_url": _quote_thread_url(post),
                    "thread_id": _quote_thread_id(post),
                    "quote_id": _quote_id(post, comment),
                    "created_utc": _post_field(post, "created_utc"),
                }
    return {}


def _collect_top_quotes_from_posts(
    top_posts: list[Hotpost],
    *,
    limit: int,
    mode: str,
) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    seen: set[str] = set()
    strict_voice_mode = mode == "rant"
    for post in top_posts:
        added_for_post = False
        for comment in (_post_field(post, "top_comments") or []):
            quote = _to_text(_post_field(comment, "body"))
            if not quote or _quote_is_noise(quote):
                continue
            key = quote.lower()
            if key in seen:
                continue
            seen.add(key)
            added_for_post = True
            quotes.append(
                {
                    "quote": quote,
                    "score": _post_field(comment, "score") or _post_field(post, "score"),
                    "subreddit": _post_field(post, "subreddit"),
                    "url": _quote_url(post, comment),
                    "thread_url": _quote_thread_url(post),
                    "thread_id": _quote_thread_id(post),
                    "quote_id": _quote_id(post, comment),
                    "created_utc": _post_field(post, "created_utc"),
                }
            )
        if not added_for_post:
            fallback_quotes = [
                (_to_text(_post_field(post, "title")), _quote_id(post)),
                (
                    _to_text(_post_field(post, "body_preview")),
                    (
                        f"{_quote_thread_id(post)}:preview"
                        if _quote_thread_id(post)
                        else _quote_thread_url(post)
                    ),
                ),
            ]
            for fallback_quote, fallback_quote_id in fallback_quotes:
                quote_allowed = bool(fallback_quote) and not _quote_is_noise(fallback_quote)
                is_title_fallback = fallback_quote_id == _quote_id(post)
                if strict_voice_mode:
                    quote_allowed = quote_allowed and _quote_has_explicit_voice(fallback_quote)
                    if is_title_fallback and _looks_like_solution_title(fallback_quote):
                        quote_allowed = False
                if not quote_allowed:
                    continue
                key = fallback_quote.lower()
                if key in seen:
                    continue
                seen.add(key)
                added_for_post = True
                quotes.append(
                    {
                        "quote": fallback_quote,
                        "score": _post_field(post, "score"),
                        "subreddit": _post_field(post, "subreddit"),
                        "url": _quote_url(post),
                        "thread_url": _quote_thread_url(post),
                        "thread_id": _quote_thread_id(post),
                        "quote_id": fallback_quote_id,
                        "created_utc": _post_field(post, "created_utc"),
                    }
                )
                break
    quotes.sort(key=_quote_quality, reverse=True)
    return quotes[:limit]

def _merge_top_quotes(
    current: Any,
    generated: list[dict[str, Any]],
    *,
    limit: int,
    top_posts: list[Hotpost],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for entry in (current if isinstance(current, list) else []) + generated:
        if not isinstance(entry, dict):
            continue
        quote = _to_text(entry.get("quote"))
        if not quote or _quote_is_noise(quote):
            continue
        context = _infer_quote_context(entry, top_posts)
        candidate = {
            "quote": quote,
            "score": entry.get("score"),
            "subreddit": entry.get("subreddit") or context.get("subreddit"),
            "url": entry.get("url") or context.get("url"),
            "thread_url": entry.get("thread_url") or context.get("thread_url"),
            "thread_id": entry.get("thread_id") or context.get("thread_id"),
            "quote_id": entry.get("quote_id") or context.get("quote_id"),
            "created_utc": entry.get("created_utc") or context.get("created_utc"),
            "why_important": entry.get("why_important"),
        }
        duplicate_idx = _quote_duplicate_index(merged, quote, url=_to_text(candidate.get("url")))
        if duplicate_idx is not None:
            for field in ("subreddit", "url", "thread_url", "thread_id", "quote_id", "created_utc", "why_important"):
                if not merged[duplicate_idx].get(field) and candidate.get(field):
                    merged[duplicate_idx][field] = candidate[field]
            if _quote_quality(candidate) > _quote_quality(merged[duplicate_idx]):
                merged[duplicate_idx] = candidate
            continue
        merged.append(candidate)
    return merged[:limit]

def _build_topic_from_post(post: Any, rank: int) -> dict[str, Any]:
    runtime = load_default_hotpost_runtime_config()
    thresholds = runtime.contract.trend_thresholds
    insights = runtime.insights
    score = int(_post_field(post, "score") or 0)
    comments = int(_post_field(post, "num_comments") or 0)
    age_hours = max(0.0, (time.time() - float(_post_field(post, "created_utc") or 0.0)) / 3600.0)
    age_days = age_hours / 24.0
    if age_hours <= insights.trending_explosive_hours and (
        score >= thresholds.explosive_score or comments >= thresholds.rising_comments * 2
    ):
        trend = "explosive"
        takeaway = f"最近 {insights.trending_explosive_hours} 小时内讨论明显抬升，值得现在就看。"
    elif age_days <= insights.trending_rising_days and (
        score >= thresholds.rising_score or comments >= thresholds.rising_comments
    ):
        trend = "rising"
        takeaway = f"最近 {insights.trending_rising_days} 天持续升温，建议继续跟踪。"
    elif age_days <= insights.trending_sustained_days:
        trend = "sustained"
        takeaway = f"最近 {insights.trending_sustained_days} 天保持热度，说明不是一次性噪音。"
    else:
        trend = "declining"
        takeaway = "讨论仍在继续，但热度已过峰值，更适合作为背景信号。"
    quote = _first_post_quote(post)
    title = _to_text(_post_field(post, "title"))
    if not title:
        return {}
    return {
        "rank": rank,
        "topic": title,
        "heat_score": int(_post_field(post, "heat_score") or (score + comments * 2)),
        "time_trend": trend,
        "key_takeaway": takeaway,
        "evidence": [
            {
                "title": title,
                "score": score,
                "comments": comments,
                "subreddit": _post_field(post, "subreddit"),
                "url": _post_field(post, "reddit_url"),
                "key_quote": quote,
            }
        ],
    }


def _ensure_common_contract(
    payload: dict[str, Any],
    *,
    mode: str,
    top_posts: list[Hotpost],
    keywords: list[str],
) -> None:
    contract = load_default_hotpost_runtime_config().contract
    generated_quotes = _collect_top_quotes_from_posts(
        top_posts,
        limit=contract.top_quotes_limit,
        mode=mode,
    )
    payload["top_quotes"] = _merge_top_quotes(
        payload.get("top_quotes"),
        generated_quotes,
        limit=contract.top_quotes_limit,
        top_posts=top_posts,
    )
    next_steps = payload.get("next_steps") or {}
    if not isinstance(next_steps, dict):
        next_steps = {}
    suggested_keywords = next_steps.get("suggested_keywords")
    if not isinstance(suggested_keywords, list) or not suggested_keywords:
        normalized_keywords = [str(k).strip() for k in keywords if str(k).strip()]
        next_steps["suggested_keywords"] = normalized_keywords[: contract.suggested_keywords_limit]
    recommended_actions = next_steps.get("recommended_actions")
    if isinstance(recommended_actions, list):
        normalized_actions = list(
            dict.fromkeys(" ".join(str(item).split()) for item in recommended_actions if str(item).strip())
        )
        if normalized_actions:
            next_steps["recommended_actions"] = normalized_actions[:3]
        else:
            next_steps.pop("recommended_actions", None)
    if "deepdive_available" not in next_steps:
        next_steps["deepdive_available"] = True
    if "deepdive_token" not in next_steps:
        next_steps["deepdive_token"] = None
    payload["next_steps"] = next_steps


def _ensure_trending_contract(payload: dict[str, Any], *, top_posts: list[Hotpost], keywords: list[str]) -> None:
    contract = load_default_hotpost_runtime_config().contract
    trending_keywords = payload.get("trending_keywords")
    if not isinstance(trending_keywords, list) or not trending_keywords:
        from_signals: list[str] = []
        for post in top_posts:
            signals = _post_field(post, "signals") or []
            if isinstance(signals, list):
                from_signals.extend(_to_text(item) for item in signals if _to_text(item))
        dedup = list(dict.fromkeys(from_signals))
        if dedup:
            payload["trending_keywords"] = dedup[: contract.suggested_keywords_limit]
        else:
            payload["trending_keywords"] = [str(k).strip() for k in keywords if str(k).strip()][
                : contract.suggested_keywords_limit
            ]


def _keyword_anchor_terms(keywords: list[str]) -> list[str]:
    anchors: list[str] = []
    for raw in keywords:
        term = _to_text(raw).lower()
        if len(term) < 4 or term in _QUERY_KEYWORD_STOP_TERMS:
            continue
        if term not in anchors:
            anchors.append(term)
    return anchors


def _quote_hits_keyword_anchor(quote: str, keyword_anchors: list[str]) -> bool:
    lowered_quote = _to_text(quote).lower()
    if not lowered_quote or not keyword_anchors:
        return False
    return any(anchor in lowered_quote for anchor in keyword_anchors)


def _ensure_rant_contract(payload: dict[str, Any], *, top_posts: list[Hotpost], keywords: list[str]) -> None:
    quotes = payload.get("top_quotes")
    if not isinstance(quotes, list):
        return None
    normalized_quotes: list[dict[str, Any]] = []
    for entry in quotes:
        if not isinstance(entry, dict):
            continue
        quote = _to_text(entry.get("quote"))
        if not quote:
            continue
        why = _to_text(entry.get("why_important"))
        if _quote_why_is_generic(why):
            why = _build_rant_quote_why_important(quote) or ""
        quote_payload = dict(entry)
        quote_payload["why_important"] = why or None
        normalized_quotes.append(quote_payload)
    first_pain_category = _first_rant_pain_category(payload)
    keyword_anchors = _keyword_anchor_terms(keywords)
    if first_pain_category and first_pain_category not in {"other", "general"}:
        aligned_quotes = [
            entry
            for entry in normalized_quotes
            if _matches_rant_category(_to_text(entry.get("quote")), first_pain_category)
            or _quote_hits_keyword_anchor(_to_text(entry.get("quote")), keyword_anchors)
        ]
        if aligned_quotes:
            remaining = [entry for entry in normalized_quotes if entry not in aligned_quotes]
            normalized_quotes = aligned_quotes + remaining
    payload["top_quotes"] = normalized_quotes
    return None


def _ensure_opportunity_contract(payload: dict[str, Any], *, top_posts: list[Hotpost]) -> None:
    return None


def _collect_contract_gaps(payload: dict[str, Any], *, mode: str, keywords: list[str]) -> list[str]:
    gaps: list[str] = []
    summary = _to_text(payload.get("summary"))
    evidence_count = int(payload.get("evidence_count") or 0)
    top_quotes = payload.get("top_quotes")
    next_steps = payload.get("next_steps") or {}

    if not summary:
        gaps.append("missing_summary")
    if evidence_count <= 0:
        gaps.append("missing_evidence")
    if not isinstance(top_quotes, list) or not top_quotes:
        gaps.append("missing_top_quotes")
    if not isinstance(next_steps, dict) or not isinstance(next_steps.get("suggested_keywords"), list) or not next_steps.get("suggested_keywords"):
        gaps.append("missing_next_step_keywords")

    if mode == "trending":
        topics = payload.get("topics")
        if not isinstance(topics, list) or not topics:
            gaps.append("missing_topics")
        else:
            first_topic = topics[0] if isinstance(topics[0], dict) else {}
            if not _to_text(first_topic.get("time_trend")):
                gaps.append("missing_time_trend")
            evidence = first_topic.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                gaps.append("missing_topic_evidence")
    elif mode == "rant":
        keyword_anchors = _keyword_anchor_terms(keywords)
        pain_points = payload.get("pain_points")
        first_pain_category = _first_rant_pain_category(payload)
        first_pain_label = ""
        if not isinstance(pain_points, list) or not pain_points:
            gaps.append("missing_pain_points")
        else:
            first_pain = pain_points[0] if isinstance(pain_points[0], dict) else {}
            first_pain_label = _to_text(first_pain.get("category"))
            sample_quotes = first_pain.get("sample_quotes") if isinstance(first_pain, dict) else []
            evidence = first_pain.get("evidence") if isinstance(first_pain, dict) else []
            has_voice = bool(
                _to_text(first_pain.get("user_voice"))
                or (isinstance(sample_quotes, list) and any(_to_text(item) for item in sample_quotes))
                or (
                    isinstance(evidence, list)
                    and any(_to_text(item.get("key_quote")) for item in evidence if isinstance(item, dict))
                )
            )
            if not has_voice:
                gaps.append("missing_pain_voice")
        if first_pain_category and first_pain_category not in {"other", "general"} and isinstance(top_quotes, list) and top_quotes:
            aligned_quote_count = sum(
                1
                for entry in top_quotes
                if isinstance(entry, dict)
                and (
                    _matches_rant_category(_to_text(entry.get("quote")), first_pain_category)
                    or _quote_hits_keyword_anchor(_to_text(entry.get("quote")), keyword_anchors)
                )
            )
            if aligned_quote_count == 0:
                gaps.append("rant_quote_off_topic")
        if summary:
            if first_pain_category in _RANT_FRICTION_CATEGORIES:
                summary_category = classify_rant_friction_category(summary, _DEFAULT_LEXICON)
            else:
                summary_category = classify_pain_category(summary, _DEFAULT_LEXICON)
        else:
            summary_category = "other"
        summary_hits_first_pain = _summary_hits_pain_category(summary, first_pain_category) or _summary_mentions_label(
            summary,
            first_pain_label,
        )
        has_rant_alignment_context = evidence_count > 0 and isinstance(pain_points, list) and bool(pain_points)
        if has_rant_alignment_context and summary and summary_category == "other" and not summary_hits_first_pain:
            gaps.append("rant_summary_not_specific")
        if (
            has_rant_alignment_context
            and summary
            and first_pain_category
            and first_pain_category not in {"other", "general"}
            and not summary_hits_first_pain
            and summary_category not in {"other", first_pain_category}
        ):
            gaps.append("rant_summary_off_topic")
        if not payload.get("migration_intent"):
            gaps.append("missing_migration_intent")
    elif mode == "opportunity":
        unmet_needs = payload.get("unmet_needs")
        if not isinstance(unmet_needs, list) or not unmet_needs:
            gaps.append("missing_unmet_needs")
        else:
            first_need = unmet_needs[0] if isinstance(unmet_needs[0], dict) else {}
            workarounds = first_need.get("current_workarounds")
            if not isinstance(workarounds, list):
                gaps.append("missing_workarounds")
        if not payload.get("market_opportunity"):
            gaps.append("missing_market_opportunity")
    return gaps


def _first_rant_pain_category(payload: dict[str, Any]) ->Optional[ str]:
    pain_points = payload.get("pain_points")
    if not isinstance(pain_points, list) or not pain_points:
        return None
    first_pain = pain_points[0] if isinstance(pain_points[0], dict) else {}
    return normalize_pain_category_label(
        _to_text(first_pain.get("category")),
        _DEFAULT_LEXICON,
    )


def _matches_rant_category(text: str, category:Optional[ str]) -> bool:
    if not category:
        return False
    normalized = _to_text(category).lower()
    if not normalized:
        return False
    if normalized in _RANT_FRICTION_CATEGORIES:
        return classify_rant_friction_category(text, _DEFAULT_LEXICON) == normalized
    return classify_pain_category(text, _DEFAULT_LEXICON) == normalized


def _summary_hits_pain_category(summary: str, category:Optional[ str]) -> bool:
    normalized_summary = _to_text(summary).lower()
    if not normalized_summary or not category:
        return False
    if category in _RANT_FRICTION_CATEGORIES:
        terms = _DEFAULT_LEXICON.rant_friction_categories.get(category) or []
    else:
        terms = _DEFAULT_LEXICON.pain_categories.get(category) or []
    return any(str(term).strip().lower() in normalized_summary for term in terms if str(term).strip())


def _summary_mentions_label(summary: str, label: str) -> bool:
    normalized_summary = _to_text(summary).lower()
    normalized_label = _to_text(label).lower()
    if not normalized_summary or not normalized_label:
        return False
    tokens = [token for token in re.split(r"[/|,，、\\s]+", normalized_label) if len(token) >= 2]
    return any(token in normalized_summary for token in tokens)


def apply_hotpost_quality_contract(
    *,
    payload: dict[str, Any],
    mode: str,
    top_posts: list[Hotpost],
    keywords: list[str],
) -> HotpostQualityContractResult:
    normalized = dict(payload)

    _ensure_common_contract(normalized, mode=mode, top_posts=top_posts, keywords=keywords)
    if mode == "trending":
        _ensure_trending_contract(normalized, top_posts=top_posts, keywords=keywords)
    elif mode == "rant":
        _ensure_rant_contract(normalized, top_posts=top_posts, keywords=keywords)
    elif mode == "opportunity":
        _ensure_opportunity_contract(normalized, top_posts=top_posts)

    gaps = _collect_contract_gaps(normalized, mode=mode, keywords=keywords)
    notes: list[str] = []
    if gaps:
        notes.append(f"质量合同未满配: {', '.join(gaps)}")

    return HotpostQualityContractResult(payload=normalized, gaps=gaps, notes=notes)


__all__ = ["HotpostQualityContractResult", "apply_hotpost_quality_contract"]
