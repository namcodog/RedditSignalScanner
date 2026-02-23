from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


_ANCHOR_STOPWORDS = {
    "store",
    "site",
    "website",
    "app",
    "platform",
    "tool",
    "product",
}

# 默认优先读取 backend/config，其次读取仓库根目录 config（便于 CI/容器只挂一份配置）。
DEFAULT_BACKEND_TOPIC_PROFILES_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "topic_profiles.yaml"
)
DEFAULT_ROOT_TOPIC_PROFILES_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "topic_profiles.yaml"
)


def _norm_text(value: str) -> str:
    return value.strip()


def normalize_subreddit(name: str) -> str:
    normalized = (name or "").strip().lower()
    if not normalized:
        return ""
    if not normalized.startswith("r/"):
        normalized = f"r/{normalized}"
    return normalized


def _dedupe_keep_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        item = _norm_text(raw)
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _sanitize_anchor_terms(values: Sequence[str]) -> list[str]:
    sanitized: list[str] = []
    for raw in values:
        item = _norm_text(raw)
        if not item:
            continue
        key = item.lower()
        if len(key) < 3:
            continue
        if key in _ANCHOR_STOPWORDS:
            continue
        sanitized.append(item)
    return _dedupe_keep_order(sanitized)


VALID_TOPIC_MODES = {"market_insight", "operations"}


def _normalize_mode(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in VALID_TOPIC_MODES:
        return raw
    return "market_insight"


@dataclass(frozen=True, slots=True)
class TopicProfile:
    id: str
    topic_name: str
    product_desc: str
    vertical: str
    allowed_communities: list[str]
    community_patterns: list[str]
    required_entities_any: list[str]
    soft_required_entities_any: list[str]
    include_keywords_any: list[str]
    exclude_keywords_any: list[str]
    mode: str = "market_insight"
    # Optional knobs for narrow topics (e.g., B2B 子题)
    preferred_days: int | None = None
    pain_min_mentions: int | None = None
    pain_min_unique_authors: int | None = None
    brand_min_mentions: int | None = None
    brand_min_unique_authors: int | None = None
    min_solutions: int | None = None
    min_sample_comments: int | None = None
    require_context_for_fetch: bool = False
    context_keywords_any: list[str] = field(default_factory=list)


def _coerce_optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def load_topic_profiles(
    path: Path | None = None,
) -> list[TopicProfile]:
    candidate_paths = (
        [path]
        if path is not None
        else [DEFAULT_BACKEND_TOPIC_PROFILES_PATH, DEFAULT_ROOT_TOPIC_PROFILES_PATH]
    )
    payload: dict[str, Any] = {}
    for candidate in candidate_paths:
        if candidate is None or not candidate.exists():
            continue
        try:
            payload = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        except Exception:
            payload = {}
        break

    raw_profiles = payload.get("topic_profiles", [])
    if not isinstance(raw_profiles, list):
        return []

    profiles: list[TopicProfile] = []
    for raw in raw_profiles:
        if not isinstance(raw, dict):
            continue
        context_keywords_raw = raw.get("context_keywords_any") or []
        if not isinstance(context_keywords_raw, list):
            context_keywords_raw = []
        require_context_for_fetch = bool(raw.get("require_context_for_fetch") or False)
        profiles.append(
            TopicProfile(
                id=str(raw.get("id") or "").strip(),
                topic_name=str(raw.get("topic_name") or "").strip(),
                product_desc=str(raw.get("product_desc") or "").strip(),
                vertical=str(raw.get("vertical") or "other").strip(),
                allowed_communities=_dedupe_keep_order(
                    [str(x) for x in (raw.get("allowed_communities") or []) if x]
                ),
                community_patterns=_dedupe_keep_order(
                    [str(x) for x in (raw.get("community_patterns") or []) if x]
                ),
                required_entities_any=_sanitize_anchor_terms(
                    [str(x) for x in (raw.get("required_entities_any") or []) if x]
                ),
                soft_required_entities_any=_dedupe_keep_order(
                    [str(x) for x in (raw.get("soft_required_entities_any") or []) if x]
                ),
                include_keywords_any=_dedupe_keep_order(
                    [str(x) for x in (raw.get("include_keywords_any") or []) if x]
                ),
                exclude_keywords_any=_dedupe_keep_order(
                    [str(x) for x in (raw.get("exclude_keywords_any") or []) if x]
                ),
                mode=_normalize_mode(raw.get("mode")),
                preferred_days=_coerce_optional_int(raw.get("preferred_days")),
                pain_min_mentions=_coerce_optional_int(raw.get("pain_min_mentions")),
                pain_min_unique_authors=_coerce_optional_int(raw.get("pain_min_unique_authors")),
                brand_min_mentions=_coerce_optional_int(raw.get("brand_min_mentions")),
                brand_min_unique_authors=_coerce_optional_int(raw.get("brand_min_unique_authors")),
                min_solutions=_coerce_optional_int(raw.get("min_solutions")),
                min_sample_comments=_coerce_optional_int(raw.get("min_sample_comments")),
                require_context_for_fetch=require_context_for_fetch,
                context_keywords_any=_dedupe_keep_order([str(x) for x in context_keywords_raw if x]),
            )
        )
    return profiles


def match_topic_profile(topic: str, profiles: Sequence[TopicProfile]) -> TopicProfile | None:
    t_lower = topic.strip().lower()
    if not t_lower:
        return None
    for profile in profiles:
        if profile.id.strip().lower() == t_lower:
            return profile
        if profile.topic_name.strip().lower() == t_lower:
            return profile
    return None


def build_search_keywords(profile: TopicProfile, topic: str) -> list[str]:
    tokens = [
        *_sanitize_anchor_terms(profile.required_entities_any),
        *_dedupe_keep_order(profile.soft_required_entities_any),
        *_dedupe_keep_order(profile.include_keywords_any),
        *_dedupe_keep_order(topic.split()),
    ]
    return _dedupe_keep_order(tokens)


def build_fetch_keywords(profile: TopicProfile, topic: str) -> list[str]:
    """
    给“样本抓取”用的关键词（偏上下文，而不是锚点词）。

    人话版：
    - required_entities_any（比如 Shopify）是“入场券”，通常通过 SQL 的 required 条件单独限制；
    - fetch_keywords 负责把内容拉到“具体语境”上（比如 ROAS/CPC/campaign/pixel 等），避免只要提到 Shopify 就全收。
    """
    if profile.context_keywords_any:
        context = list(profile.context_keywords_any)
    else:
        context = [*profile.include_keywords_any, *profile.soft_required_entities_any]

    tokens = [
        *_dedupe_keep_order(context),
        *_dedupe_keep_order(topic.split()),
    ]
    # 当启用 require_context_for_fetch 时，显式剔除锚点词，避免“只提到 Shopify 就算命中”
    if profile.require_context_for_fetch:
        anchors = {t.strip().lower() for t in profile.required_entities_any if t and t.strip()}
        tokens = [t for t in tokens if t.strip().lower() not in anchors]
    return _dedupe_keep_order(tokens)


def context_keywords_for_profile(profile: TopicProfile) -> list[str]:
    """返回“语境关键词”列表（用于窄题双钥匙过滤）。"""
    if profile.context_keywords_any:
        return _dedupe_keep_order(profile.context_keywords_any)
    return _dedupe_keep_order([*profile.include_keywords_any, *profile.soft_required_entities_any])


def filter_items_by_profile_context(
    items: Sequence[Mapping[str, object]],
    profile: TopicProfile,
    *,
    text_keys: Sequence[str] = ("title", "text", "body"),
) -> list[Mapping[str, object]]:
    """
    双钥匙的第二把钥匙：只保留“明确命中语境关键词”的内容。

    适用场景：
    - topic 很窄（比如 Shopify Ads/ROAS 这类），不能让“只提到 Shopify 的泛运营贴”把样本稀释掉。
    """
    if not profile.require_context_for_fetch:
        return list(items)

    terms = [t.lower() for t in context_keywords_for_profile(profile) if t]
    if not terms:
        return list(items)

    kept: list[Mapping[str, object]] = []
    for item in items:
        parts: list[str] = []
        for key in text_keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)
        if not parts:
            continue
        t_lower = " ".join(parts).lower()
        if any(term in t_lower for term in terms):
            kept.append(item)
    return kept


def filter_relevance_map_with_profile(
    relevance_map: Mapping[str, int],
    profile: TopicProfile,
    *,
    boost_allowed_to: int = 10000,
) -> dict[str, int]:
    allowed = {normalize_subreddit(c) for c in profile.allowed_communities}
    allowed = {c for c in allowed if c}
    patterns = [p.strip().lower() for p in profile.community_patterns if p and p.strip()]

    filtered: dict[str, int] = {}
    for raw_name, raw_count in relevance_map.items():
        name = normalize_subreddit(str(raw_name))
        if not name:
            continue
        if allowed:
            if name in allowed:
                filtered[name] = max(int(raw_count or 0), boost_allowed_to)
                continue
            if patterns and any(pat in name for pat in patterns):
                filtered[name] = int(raw_count or 0)
                continue
            continue
        if patterns and any(pat in name for pat in patterns):
            filtered[name] = int(raw_count or 0)
            continue
        filtered[name] = int(raw_count or 0)

    for comm in allowed:
        filtered.setdefault(comm, boost_allowed_to)

    return filtered


def topic_profile_allows_community(profile: TopicProfile, community: str) -> bool:
    name = normalize_subreddit(community)
    if not name:
        return False
    allowed = {normalize_subreddit(c) for c in profile.allowed_communities}
    allowed = {c for c in allowed if c}
    if name in allowed:
        return True
    patterns = [p.strip().lower() for p in profile.community_patterns if p and p.strip()]
    return bool(patterns) and any(pat in name for pat in patterns)


def topic_profile_blocklist_keywords(profile: TopicProfile) -> list[str]:
    return _dedupe_keep_order(profile.exclude_keywords_any)


__all__ = [
    "TopicProfile",
    "build_fetch_keywords",
    "build_search_keywords",
    "context_keywords_for_profile",
    "filter_items_by_profile_context",
    "filter_relevance_map_with_profile",
    "load_topic_profiles",
    "match_topic_profile",
    "normalize_subreddit",
    "topic_profile_allows_community",
    "topic_profile_blocklist_keywords",
]
