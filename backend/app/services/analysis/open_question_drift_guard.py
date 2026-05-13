from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional, Any, Mapping, Sequence

from app.services.analysis.analysis_collection_support import (
    CommunityProfile,
    OpenTopicRoute,
    normalise_community_name,
)
from app.services.analysis.open_question_query_plan import OpenQuestionQueryPlan

_SPECIFIC_ENTITY_RE = re.compile(
    r"https?://\S+|[A-Za-z]+[0-9][A-Za-z0-9._/-]*|[A-Za-z]+(?:[./_-][A-Za-z0-9]+)+|[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+|[A-Z]{2,}[A-Za-z0-9._/-]*"
)
_MIN_RETRIEVAL_SIGNAL = 5
_MIN_ROUTE_SHARE = 0.2
_LOW_MARGIN_THRESHOLD = 0.12


@dataclass(frozen=True)
class OpenQuestionDriftGuardResult:
    relax_route: bool
    reasons: tuple[str, ...]
    diagnostics: dict[str, Any]


def _casefold_set(values: Sequence[str]) -> set[str]:
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def _extract_specific_entities(text: str) -> tuple[str, ...]:
    entities: list[str] = []
    seen: set[str] = set()
    for match in _SPECIFIC_ENTITY_RE.findall(text or ""):
        normalized = str(match).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        entities.append(normalized)
    return tuple(entities)


def _community_name_from_post(post: Any) -> str:
    if isinstance(post, Mapping):
        raw = (
            post.get("subreddit")
            or post.get("community")
            or post.get("subreddit_name_prefixed")
            or ""
        )
    else:
        raw = getattr(post, "subreddit", "")
    return normalise_community_name(str(raw or ""))


def _build_retrieval_counter(
    *,
    search_posts: Sequence[Any],
    semantic_counts:Optional[ Mapping[str, int]],
) -> Counter[str]:
    counter: Counter[str] = Counter()
    for post in search_posts:
        community = _community_name_from_post(post)
        if community != "r/unknown":
            counter[community] += 1
    # `semantic_counts` is a broader topic-probe signal. Once raw search hits exist,
    # we only trust the search layer for drift decisions, otherwise the guard
    # becomes too easy to over-trigger on noisy semantic expansion.
    if counter:
        return counter
    for name, count in (semantic_counts or {}).items():
        community = normalise_community_name(str(name or ""))
        if community != "r/unknown" and int(count or 0) > 0:
            counter[community] += int(count)
    return counter


def _build_profile_map(
    community_profiles: Sequence[CommunityProfile],
) -> dict[str, CommunityProfile]:
    profile_map: dict[str, CommunityProfile] = {}
    for profile in community_profiles:
        normalized = normalise_community_name(profile.name)
        if normalized == "r/unknown":
            continue
        profile_map[normalized] = profile
        if normalized.startswith("r/"):
            profile_map[normalized[2:]] = profile
    return profile_map


def _matches_route_community(
    community_name: str,
    route:Optional[ OpenTopicRoute],
    profile_map: Mapping[str, CommunityProfile],
) -> bool:
    if route is None:
        return True
    normalized = normalise_community_name(community_name)
    if normalized in route.allowed_names:
        return True
    profile = (
        profile_map.get(normalized)
        or profile_map.get(normalized.removeprefix("r/"))
        or profile_map.get(f"r/{normalized}")
    )
    if profile is None:
        return False
    for category in profile.categories:
        category_text = str(category)
        if category_text.startswith("warzone:") and category_text.split("warzone:", 1)[1] == route.warzone:
            return True
    return False


def evaluate_open_question_drift_guard(
    *,
    query_plan: OpenQuestionQueryPlan,
    open_topic_route:Optional[ OpenTopicRoute],
    search_posts: Sequence[Any] = (),
    semantic_counts:Optional[ Mapping[str, int]] = None,
    community_profiles: Sequence[CommunityProfile] = (),
) -> OpenQuestionDriftGuardResult:
    query_texts = tuple(
        text.strip()
        for text in (query_plan.route_query_en, *query_plan.retrieve_queries_en)
        if str(text or "").strip()
    )
    joined_query_text = "\n".join(query_texts)
    must_keep_all = tuple(query_plan.must_keep)
    preserved = tuple(
        entity
        for entity in must_keep_all
        if entity.casefold() in joined_query_text.casefold()
    )
    missing = tuple(entity for entity in must_keep_all if entity not in preserved)
    preservation_rate = 1.0
    if must_keep_all:
        preservation_rate = round(len(preserved) / len(must_keep_all), 3)

    original_specific = _casefold_set(
        (*must_keep_all, *_extract_specific_entities(query_plan.rerank_query))
    )
    generated_specific = _extract_specific_entities(joined_query_text)
    invented_entities = tuple(
        entity
        for entity in generated_specific
        if entity.casefold() not in original_specific
    )

    retrieval_counter = _build_retrieval_counter(
        search_posts=search_posts,
        semantic_counts=semantic_counts,
    )
    retrieval_total = sum(retrieval_counter.values())
    profile_map = _build_profile_map(community_profiles)
    route_hits = sum(
        count
        for name, count in retrieval_counter.items()
        if _matches_route_community(name, open_topic_route, profile_map)
    )
    route_share = round(route_hits / retrieval_total, 3) if retrieval_total else 1.0
    outside_top = next(
        (
            (name, count)
            for name, count in retrieval_counter.most_common()
            if not _matches_route_community(name, open_topic_route, profile_map)
        ),
        None,
    )
    inside_top = next(
        (
            (name, count)
            for name, count in retrieval_counter.most_common()
            if _matches_route_community(name, open_topic_route, profile_map)
        ),
        None,
    )

    reasons: list[str] = []
    if open_topic_route is not None and missing:
        reasons.append("must_keep_drift")
    if open_topic_route is not None and invented_entities:
        reasons.append("invented_entity")
    if open_topic_route is not None and retrieval_total >= _MIN_RETRIEVAL_SIGNAL:
        outside_count = int(outside_top[1]) if outside_top is not None else 0
        inside_count = int(inside_top[1]) if inside_top is not None else 0
        if route_hits == 0:
            reasons.append("retrieval_consistency")
        elif (
            route_share < _MIN_ROUTE_SHARE
            and outside_count >= _MIN_RETRIEVAL_SIGNAL
            and outside_count > inside_count
            and float(open_topic_route.margin) <= _LOW_MARGIN_THRESHOLD
        ):
            reasons.append("retrieval_consistency")
        elif (
            float(open_topic_route.margin) <= _LOW_MARGIN_THRESHOLD
            and outside_count > inside_count
        ):
            reasons.append("retrieval_consistency")

    diagnostics = {
        "must_keep": list(must_keep_all),
        "preserved_must_keep": list(preserved),
        "missing_must_keep": list(missing),
        "entity_preservation_rate": preservation_rate,
        "invented_entities": list(invented_entities),
        "retrieval_total": retrieval_total,
        "route_hits": route_hits,
        "route_share": route_share,
        "top_retrieval_communities": [
            {"name": name, "count": int(count)}
            for name, count in retrieval_counter.most_common(5)
        ],
        "reasons": list(dict.fromkeys(reasons)),
        "relax_route": bool(reasons),
    }
    return OpenQuestionDriftGuardResult(
        relax_route=bool(reasons),
        reasons=tuple(dict.fromkeys(reasons)),
        diagnostics=diagnostics,
    )


__all__ = [
    "OpenQuestionDriftGuardResult",
    "evaluate_open_question_drift_guard",
]
