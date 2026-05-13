from __future__ import annotations

from collections import Counter
from typing import Optional, Any, Dict, List, Sequence

from app.services.analysis.analysis_collection_support import OpenTopicRoute
from app.services.analysis.evidence_selection import (
    EvidenceSelectionInput,
    select_evidence_posts,
)
from app.services.analysis.open_topic_anchor_bridge import bridge_open_topic_anchors
from app.services.analysis.topic_profiles import (
    TopicProfile,
    filter_items_by_profile_context,
    normalize_subreddit,
)

_DEFAULT_EXPANSION_STOPWORDS: set[str] = {
    "machine",
    "home",
    "best",
    "review",
    "reviews",
    "reddit",
    "r",
    "advice",
    "help",
    "store",
    "shop",
    "buy",
    "sell",
    "online",
    "question",
    "discussion",
    "comment",
    "product",
    "products",
    "com",
    "www",
    "http",
    "https",
}


def tokenise(text: str) -> List[str]:
    tokens: List[str] = []
    current: List[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current.clear()
    if current:
        tokens.append("".join(current))
    return tokens


def build_reddit_search_queries(*, tokens: Sequence[str], lookback_days: int) -> list[str]:
    """
    Build compact Reddit search queries from keyword tokens.

    Human intent (Phase105/106, plain language):
    - Reddit search is our "narrow topic booster": we want queries that include the anchor
      and some context, without polluting the query with non-English tokens.
    """

    def _is_ascii(text: str) -> bool:
        try:
            text.encode("ascii")
            return True
        except UnicodeEncodeError:
            return False

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        term = str(raw or "").strip()
        if not term:
            continue
        if not _is_ascii(term):
            continue
        if len(term) < 2:
            continue
        if len(term) > 40:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(term)
        if len(cleaned) >= 12:
            break

    if not cleaned:
        return []

    query1 = " ".join(cleaned[:3]).strip()
    query2 = (
        " ".join(cleaned[1:4]).strip()
        if len(cleaned) > 3
        else " ".join(cleaned[:2]).strip()
    )
    queries = [q for q in (query1, query2) if q]

    if lookback_days >= 365 and len(cleaned) >= 2:
        queries.append(" ".join(cleaned[:2]).strip())

    out: list[str] = []
    seen_q: set[str] = set()
    for q in queries:
        key = q.lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        out.append(q)
    return out


def extract_keywords(description: str, max_keywords: int = 12) -> List[str]:
    tokens = [token for token in tokenise(description) if len(token) >= 3]
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(max_keywords)]


def augment_keywords(base: Sequence[str], description: str) -> List[str]:
    """Augment keywords with common英中领域同义词，提升匹配度（尤其中文输入）。"""
    ordered: list[str] = []
    seen: set[str] = set()

    def _append_many(values: Sequence[str]) -> None:
        for raw in values:
            item = str(raw or "").strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)

    _append_many(base)
    desc_lower = description.lower()
    desc_tokens = set(tokenise(description))

    def _matches_variant(variant: str) -> bool:
        normalized = str(variant or "").strip().lower()
        if not normalized:
            return False
        if " " in normalized:
            return normalized in desc_lower
        return normalized in desc_tokens

    canon = {
        "ai": ["ai", "artificial", "machine", "ml"],
        "note": ["note", "notes", "notetaking", "notebook"],
        "summary": ["summary", "summarize", "summarise", "summarizing"],
        "startup": [
            "startup",
            "startups",
            "founder",
            "founders",
            "entrepreneur",
            "entrepreneurs",
        ],
        "market": ["market", "marketing", "growth", "insight", "insights"],
        "product": ["product", "pm", "roadmap", "ux", "research"],
        "family": ["baby", "newborn", "parenting", "feeding", "sleep"],
        "coffee": ["coffee", "espresso", "grinder", "brew", "beans"],
        "frugal": ["frugal", "budget", "save money", "subscription", "bill"],
        "outdoor": ["onebag", "travel", "backpack", "camping", "hiking"],
        "home": ["home", "cleaning", "vacuum", "storage", "organization"],
        "edc": ["edc", "carry", "organizer"],
    }
    zh_triggers = {
        "笔记": ["note", "notes"],
        "总结": ["summary", "summarize"],
        "创业": ["startup", "entrepreneur"],
        "市场": ["market", "insight"],
        "洞察": ["insight"],
        "产品": ["product"],
        "AI": ["ai"],
        "育儿": ["baby", "parenting"],
        "宝宝": ["baby", "newborn"],
        "新生儿": ["newborn", "baby"],
        "喂养": ["feeding", "baby"],
        "夜奶": ["feeding", "sleep"],
        "睡眠": ["sleep", "routine"],
        "家人协作": ["parenting", "routine"],
        "咖啡": ["coffee", "brew"],
        "浓缩": ["espresso", "shot"],
        "磨豆": ["grinder", "espresso"],
        "萃取": ["espresso", "brew"],
        "豆子": ["beans", "coffee"],
        "省钱": ["frugal", "save money"],
        "订阅": ["subscription", "bill"],
        "扣费": ["subscription", "payment"],
        "账单": ["bill", "budget"],
        "预算": ["budget", "save money"],
        "旅行": ["travel", "onebag"],
        "露营": ["camping", "outdoor"],
        "徒步": ["hiking", "outdoor"],
        "背包": ["backpack", "travel"],
        "收纳": ["organizer", "storage"],
        "家居": ["home", "storage"],
        "清洁": ["cleaning", "vacuum"],
        "吸尘": ["vacuum", "cleaning"],
        "整理": ["organization", "storage"],
        "口袋": ["edc", "carry"],
        "钥匙": ["edc", "organizer"],
        "手电": ["flashlight", "edc"],
        "多工具": ["multitool", "edc"],
    }
    for root, variants in canon.items():
        if _matches_variant(root) or any(v in seen for v in variants):
            _append_many(variants)
    for zh, variants in zh_triggers.items():
        if zh in description:
            _append_many(variants)
    _append_many(
        bridge_open_topic_anchors(
            description=description,
            existing_keywords=tuple(ordered),
        )
    )
    return ordered


def filter_posts_by_keywords(
    posts: Sequence[Dict[str, Any]], keywords: Sequence[str]
) -> List[Dict[str, Any]]:
    if not posts or not keywords:
        return list(posts)
    keys = [k.lower() for k in keywords if k]
    filtered: List[Dict[str, Any]] = []
    for post in posts:
        title = str(post.get("title", "")).lower()
        summary = str(post.get("summary", "")).lower()
        text = f"{title} {summary}"
        if any(k in text for k in keys):
            filtered.append(post)
    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def apply_query_focus_filter(
    posts: Sequence[Dict[str, Any]],
    product_description: str,
    keywords:Optional[ Sequence[str]] = None,
    open_topic_route:Optional[ OpenTopicRoute] = None,
) -> List[Dict[str, Any]]:
    if not posts:
        return []
    selection = select_evidence_posts(
        posts,
        EvidenceSelectionInput(
            product_description=product_description,
            keywords=tuple(keywords or ()),
            route_reasons=tuple(open_topic_route.reasons) if open_topic_route else (),
            preferred_communities=tuple(
                profile.name for profile in open_topic_route.seed_profiles
            )
            if open_topic_route
            else (),
        ),
    )
    return selection.posts


def apply_keyword_stopwords(
    keywords: Sequence[str],
    blacklist_config:Optional[ Any] = None,
) -> List[str]:
    if not keywords:
        return []

    stopwords: set[str] = set(_DEFAULT_EXPANSION_STOPWORDS)
    if blacklist_config is not None:
        try:
            stopwords.update(
                getattr(blacklist_config, "semantic_expansion_stopwords", set())
            )
        except Exception:
            pass
        try:
            stopwords.update(getattr(blacklist_config, "filter_keywords", set()))
        except Exception:
            pass

    filtered: list[str] = []
    seen: set[str] = set()
    for word in keywords:
        raw = str(word or "").strip()
        if not raw:
            continue
        lowered = raw.lower()
        if lowered in stopwords or lowered in seen:
            continue
        seen.add(lowered)
        filtered.append(raw)
    return filtered


def filter_posts_by_blocklist(
    posts: Sequence[Dict[str, Any]],
    blocklist: Sequence[str],
) -> List[Dict[str, Any]]:
    if not posts or not blocklist:
        return list(posts)
    keys = [k.lower() for k in blocklist if k]
    if not keys:
        return list(posts)

    filtered: List[Dict[str, Any]] = []
    for post in posts:
        title = str(post.get("title", "")).lower()
        summary = str(post.get("summary", "")).lower()
        body = str(post.get("body", "")).lower()
        text = f"{title} {summary} {body}"
        if any(k in text for k in keys):
            continue
        filtered.append(post)

    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def filter_posts_by_blacklist_config(
    posts: Sequence[Dict[str, Any]],
    blacklist_config:Optional[ Any],
) -> List[Dict[str, Any]]:
    if not posts or blacklist_config is None:
        return list(posts)

    filtered: List[Dict[str, Any]] = []
    for post in posts:
        title = str(post.get("title", "") or "")
        summary = str(post.get("summary", "") or "")
        body = str(post.get("body", "") or "")
        text = f"{title} {summary} {body}".strip()
        author = str(post.get("author") or post.get("author_name") or "").strip()
        try:
            if author and blacklist_config.is_author_blacklisted(author):
                continue
        except Exception:
            pass
        try:
            if blacklist_config.matches_spam_pattern(text):
                continue
        except Exception:
            pass
        try:
            if blacklist_config.should_filter_post(title, f"{summary} {body}"):
                continue
        except Exception:
            pass
        filtered.append(post)

    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def apply_topic_profile_context_filter(
    posts: Sequence[Dict[str, Any]],
    profile: TopicProfile,
) -> List[Dict[str, Any]]:
    if not posts:
        return []
    if not profile.require_context_for_fetch:
        return list(posts)
    filtered = list(
        filter_items_by_profile_context(
            posts,
            profile,
            text_keys=("title", "summary", "text", "body", "selftext"),
        )
    )
    return filtered


def apply_topic_profile_required_filter(
    posts: Sequence[Dict[str, Any]],
    profile: TopicProfile,
) -> List[Dict[str, Any]]:
    if not posts:
        return []
    required = [
        str(term).strip().lower()
        for term in (profile.required_entities_any or [])
        if str(term).strip()
    ]
    if not required:
        return list(posts)

    kept: list[Dict[str, Any]] = []
    for post in posts:
        raw_subreddit = str(post.get("subreddit") or "").strip()
        subreddit = normalize_subreddit(raw_subreddit)
        if subreddit:
            slug = subreddit.removeprefix("r/").strip().lower()
            if slug:
                for term in required:
                    if not term or " " in term or len(term) < 3:
                        continue
                    if term in slug:
                        kept.append(post)
                        break
                else:
                    pass
                if kept and kept[-1] is post:
                    continue

        title = str(post.get("title", "")).lower()
        summary = str(post.get("summary", "")).lower()
        body = str(post.get("body", "")).lower()
        text = str(post.get("text", "")).lower()
        selftext = str(post.get("selftext", "")).lower()
        hay = f"{title} {summary} {body} {text} {selftext}"
        if any(term in hay for term in required):
            kept.append(post)
    return kept
