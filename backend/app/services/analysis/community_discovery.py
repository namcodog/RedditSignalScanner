"""
Step 1: Community discovery heuristics aligned with PRD/PRD-03-分析引擎.md.

Day 6 upgrades the initial placeholder implementation to use the TF-IDF keyword
extraction module, apply weighted scoring, and enforce category diversity so
frontend and QA teams receive deterministic yet realistic results.
"""

from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple, TYPE_CHECKING

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.analysis.keyword_extraction import KeywordExtractionResult, extract_keywords

if TYPE_CHECKING:
    from app.services.analysis_engine import CommunityProfile
else:  # pragma: no cover - runtime type fallback
    CommunityProfile = Any  # type: ignore[assignment]


_DESCRIPTION_WEIGHT = 0.4
_ACTIVITY_WEIGHT = 0.3
_QUALITY_WEIGHT = 0.3
_MAX_CATEGORY_DUPLICATES = 5
_DIVERSITY_BONUS = 0.05
_DIVERSITY_MAX_BONUS = 0.1


@dataclass(frozen=True)
class Community:
    """Lightweight projection exposed to step 2 (data collection)."""

    name: str
    categories: Sequence[str]
    description_keywords: Sequence[str]
    daily_posts: int
    avg_comment_length: int
    relevance_score: float


async def discover_communities(
    product_description: str,
    *,
    max_communities: int = 20,
    cache_hit_rate: float = 0.7,
) -> List[Community]:
    """
    Discover the most relevant Reddit communities for a product description.
    """

    if not product_description or len(product_description.strip()) < 10:
        raise ValueError("product_description must contain at least 10 characters.")

    keyword_result = await extract_keywords(
        product_description,
        max_keywords=20,
    )
    target = _calculate_target_communities(cache_hit_rate)
    pool = await _load_community_pool()
    scores = _score_communities(keyword_result, pool)
    selected = _select_diverse_top_k(
        scores,
        k=min(target, max_communities, len(pool)),
    )

    # Simulate IO to keep async signature future-proof.
    await asyncio.sleep(0)
    return selected


def _score_communities(
    keywords: KeywordExtractionResult,
    community_pool: Sequence[CommunityProfile],
) -> Dict[CommunityProfile, float]:
    scores: Dict[CommunityProfile, float] = {}
    for community in community_pool:
        description_score = _calculate_description_match(
            keywords,
            community.description_keywords,
        )
        activity_score = min(community.daily_posts / 200.0, 1.0)
        quality_score = min(community.avg_comment_length / 120.0, 1.0)

        total = round(
            (description_score * _DESCRIPTION_WEIGHT)
            + (activity_score * _ACTIVITY_WEIGHT)
            + (quality_score * _QUALITY_WEIGHT),
            4,
        )
        scores[community] = total
    return scores


def _calculate_description_match(
    keywords: KeywordExtractionResult,
    community_keywords: Sequence[str],
) -> float:
    if not keywords.keywords or not community_keywords:
        return 0.0

    product_text = " ".join(keywords.keywords).strip()
    community_text = " ".join(community_keywords).strip()
    if not product_text or not community_text:
        return 0.0

    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([product_text, community_text])
    except ValueError:
        return _fallback_description_overlap(keywords.weights, community_keywords)

    similarity = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    if math.isnan(similarity) or similarity < 0.0:
        return 0.0
    return min(similarity, 1.0)


def _fallback_description_overlap(
    keyword_weights: Dict[str, float],
    community_keywords: Sequence[str],
) -> float:
    if not keyword_weights or not community_keywords:
        return 0.0

    denominator = sum(keyword_weights.values())
    if denominator <= 0.0:
        return 0.0

    overlap = sum(keyword_weights.get(term, 0.0) for term in community_keywords)
    return min(overlap / denominator, 1.0)


def _select_diverse_top_k(
    scored: Dict[CommunityProfile, float],
    *,
    k: int,
    max_per_category: int = _MAX_CATEGORY_DUPLICATES,
) -> List[Community]:
    if k <= 0 or not scored:
        return []

    sorted_items = sorted(scored.items(), key=lambda item: item[1], reverse=True)
    category_counts: Dict[str, int] = defaultdict(int)
    selected: List[Community] = []
    overflow: List[Tuple[CommunityProfile, float]] = []

    for profile, base_score in sorted_items:
        if len(selected) >= k:
            break

        if _is_category_limit_reached(profile.categories, category_counts, max_per_category):
            overflow.append((profile, base_score))
            continue

        bonus = _calculate_category_bonus(profile.categories, category_counts)
        final_score = min(base_score + bonus, 1.0)

        selected.append(_build_community(profile, final_score))
        for category in profile.categories:
            category_counts[category] += 1

    if len(selected) < k:
        for profile, base_score in overflow:
            if len(selected) >= k:
                break
            if _is_category_limit_reached(profile.categories, category_counts, max_per_category):
                continue
            selected.append(_build_community(profile, min(base_score, 1.0)))
            for category in profile.categories:
                category_counts[category] += 1

    selected.sort(key=lambda community: community.relevance_score, reverse=True)
    return selected


def _is_category_limit_reached(
    categories: Sequence[str],
    category_counts: Dict[str, int],
    max_per_category: int,
) -> bool:
    return any(category_counts[category] >= max_per_category for category in categories)


def _calculate_category_bonus(
    categories: Sequence[str],
    category_counts: Dict[str, int],
) -> float:
    unseen_categories = sum(
        1 for category in categories if category_counts.get(category, 0) == 0
    )
    return min(unseen_categories * _DIVERSITY_BONUS, _DIVERSITY_MAX_BONUS)


def _build_community(profile: CommunityProfile, score: float) -> Community:
    return Community(
        name=profile.name,
        categories=profile.categories,
        description_keywords=profile.description_keywords,
        daily_posts=profile.daily_posts,
        avg_comment_length=profile.avg_comment_length,
        relevance_score=round(score, 4),
    )


def _calculate_target_communities(cache_hit_rate: float) -> int:
    if cache_hit_rate > 0.8:
        return 30
    if cache_hit_rate > 0.6:
        return 20
    return 10


async def _load_community_pool() -> List[CommunityProfile]:
    await asyncio.sleep(0)
    # Only use DB-backed pool when explicitly enabled to avoid
    # introducing external dependencies in unit tests.
    import os

    use_db = os.getenv("COMMUNITY_POOL_FROM_DB", "0").strip().lower() in {"1", "true", "yes"}
    if use_db:
        try:
            from app.services.community_pool_loader import CommunityPoolLoader  # type: ignore

            loader = CommunityPoolLoader()
            profiles = await loader.load_community_pool()
            if profiles:
                return list(profiles)
        except Exception:
            # Fallback if DB not configured or loader unavailable
            pass

    from app.services.analysis_engine import COMMUNITY_CATALOGUE
    return list(COMMUNITY_CATALOGUE)


__all__ = [
    "Community",
    "discover_communities",
]
