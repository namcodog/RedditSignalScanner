from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


_TARGET_SCOPE = "business-growth-ops"
_TARGET_PACKS = {"organic-discovery", "funnel-conversion"}
_TITLE_BLOCK_TERMS = (
    "weekly",
    "megathread",
    "mega thread",
    "news recap",
    "news stories",
    "roundup",
    "round-up",
    "welcome",
    "rules",
    "please read",
    "group rules",
    "questions thread",
    "feedback thread",
    "soliciting recommendations",
    "digest",
)

_ORGANIC_SOURCE_TERMS = (
    "organic traffic",
    "search traffic",
    "google traffic",
    "content marketing",
    "search clicks",
    "search impressions",
    "google discover",
    "discover traffic",
    "affiliate traffic",
    "newsletter traffic",
    "referral traffic",
    "content traffic",
    "organic leads",
    "email list",
    "clean lists",
    "newsletter",
    "substack",
    "open rates",
    "click rates",
    "pinterest traffic",
)
_ORGANIC_QUALITY_TERMS = (
    "traffic quality",
    "lead quality",
    "low intent",
    "high intent",
    "wrong audience",
    "unqualified",
    "quality dropped",
    "quality drop",
    "converts worse",
    "conversion dropped",
    "clicks but no demos",
    "clicks but no buyers",
    "traffic up but",
    "impressions up but",
    "more traffic less revenue",
    "less qualified",
    "buyers not clicks",
    "junk traffic",
    "very little google traffic",
    "clean lists are still trash",
    "low open rates",
    "open rate dropped",
    "seeing roi anymore",
    "no demos from organic",
    "still trash",
    "feels broken",
    "recommends our competitors",
)
_ORGANIC_BLOCK_TERMS = (
    "ahrefs",
    "semrush",
    "screaming frog",
    "google search console",
    "gsc",
    "best seo tool",
    "seo tool",
    "geo tool",
    "what is seo",
    "what is geo",
    "tool stack",
    "google ads",
    "meta ads",
    "facebook ads",
    "paid spend",
    "adwords",
    "ppc",
)

_FUNNEL_EVENT_TERMS = (
    "checkout",
    "cart",
    "conversion",
    "pricing page",
    "demo",
    "demos",
    "booking",
    "appointment",
    "lead form",
    "form submission",
    "payment processor",
    "shopify payments",
    "payout",
    "payouts",
    "shop pay",
    "shipping",
    "shipping option",
    "shipping method",
    "signup",
    "sign up",
    "landing page",
    "product page",
    "shipping cost",
)
_FUNNEL_LEAK_TERMS = (
    "drop off",
    "drops off",
    "drops",
    "drop",
    "abandoned",
    "abandonment",
    "no demos",
    "no buyers",
    "buyers disappear",
    "disappear",
    "low intent",
    "friction",
    "leak",
    "leakage",
    "bounce",
    "not convert",
    "conversion dropped",
    "completion drops",
    "checkout completion drops",
    "1% conversion",
    "not showing",
    "shut you down",
    "froze",
    "trusting a new ecommerce site",
    "form spam",
    "unqualified leads",
    "doesn't close",
    "click but no",
    "clicks but no",
)
_FUNNEL_REPLACEMENT_TERMS = (
    "need a new",
    "new payment processor",
    "switch",
    "switching",
    "replace",
    "replacement",
    "shut you down",
    "hold funds",
    "funds held",
    "funds on hold",
    "reserve",
    "frozen",
    "froze",
    "get rid of",
    "under review",
    "won't tell me why",
    "decline",
    "declined",
    "blocked",
    "disabled",
)
_FUNNEL_BLOCK_TERMS = (
    "rate my landing page",
    "landing page roast",
    "what is a good conversion rate",
    "conversion rate benchmark",
    "cro agency",
    "cro tips",
    "best practices",
)


def uses_growth_pack_intake_path(scope_id: str, topic_pack_id: str | None) -> bool:
    return scope_id == _TARGET_SCOPE and (topic_pack_id or "") in _TARGET_PACKS


def is_growth_pack_title_blocked(title: str) -> bool:
    lowered = title.lower()
    return any(_contains_term(lowered, term) for term in _TITLE_BLOCK_TERMS)


def match_growth_pack_keywords(topic_pack_id: str, title: str, selftext: str) -> list[str]:
    text = f"{title} {selftext}".lower()
    if topic_pack_id == "organic-discovery":
        if any(_contains_term(text, term) for term in _ORGANIC_BLOCK_TERMS):
            return []
        source_hits = [term for term in _ORGANIC_SOURCE_TERMS if _contains_term(text, term)]
        quality_hits = [term for term in _ORGANIC_QUALITY_TERMS if _contains_term(text, term)]
        if not source_hits or not quality_hits:
            return []
        return _dedupe([*source_hits[:1], *quality_hits[:2]])
    if topic_pack_id == "funnel-conversion":
        if any(_contains_term(text, term) for term in _FUNNEL_BLOCK_TERMS):
            return []
        event_hits = [term for term in _FUNNEL_EVENT_TERMS if _contains_term(text, term)]
        leak_hits = [term for term in _FUNNEL_LEAK_TERMS if _contains_term(text, term)]
        replacement_hits = [term for term in _FUNNEL_REPLACEMENT_TERMS if _contains_term(text, term)]
        if not event_hits:
            return []
        if not leak_hits:
            if {"payment processor", "shopify payments", "shop pay"} & set(event_hits) and replacement_hits:
                return _dedupe([*event_hits[:1], *replacement_hits[:2]])
            return []
        return _dedupe([*event_hits[:1], *leak_hits[:2]])
    return []


def resolve_growth_pack_signal_level(post: Any) -> str | None:
    age_hours = (datetime.now(timezone.utc).timestamp() - float(post.created_utc)) / 3600
    if age_hours <= 72 and (int(post.score) >= 120 or int(post.num_comments) >= 24):
        return "hot"
    if age_hours <= 24 * 7 and (int(post.score) >= 35 or int(post.num_comments) >= 10):
        return "rising"
    if age_hours <= 24 * 30 and (int(post.score) >= 18 or int(post.num_comments) >= 6):
        return "sustained"
    return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text) is not None


__all__ = [
    "is_growth_pack_title_blocked",
    "match_growth_pack_keywords",
    "resolve_growth_pack_signal_level",
    "uses_growth_pack_intake_path",
]
