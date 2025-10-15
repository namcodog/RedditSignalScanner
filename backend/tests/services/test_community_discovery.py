from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Sequence

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.services.analysis import Community, discover_communities
from app.services.analysis.community_discovery import (
    _calculate_description_match,
    _fallback_description_overlap,
    _score_communities,
    _select_diverse_top_k,
    _calculate_target_communities,
)
from app.services.analysis.keyword_extraction import KeywordExtractionResult
from app.services.analysis_engine import CommunityProfile


pytestmark = pytest.mark.anyio


async def test_discover_communities_respects_limits() -> None:
    communities = await discover_communities(
        "AI tool for growth teams to automate insight discovery and reporting.",
        max_communities=15,
        cache_hit_rate=0.75,
    )

    assert 0 < len(communities) <= 15
    assert all(isinstance(entry, Community) for entry in communities)
    scores = [community.relevance_score for community in communities]
    assert scores == sorted(scores, reverse=True)


async def test_target_adjustment_based_on_cache_rate() -> None:
    description = "Productivity workflow automation for startups and product teams."
    high_cache = await discover_communities(
        description,
        max_communities=40,
        cache_hit_rate=0.9,
    )
    low_cache = await discover_communities(
        description,
        max_communities=40,
        cache_hit_rate=0.5,
    )
    assert len(high_cache) >= len(low_cache)


def test_score_prefers_highly_relevant_community() -> None:
    keywords = KeywordExtractionResult(
        keywords=["productivity", "note", "workflow"],
        weights={"productivity": 1.0, "note": 0.8, "workflow": 0.6},
        total_keywords=3,
    )
    relevant = CommunityProfile(
        name="r/productivity",
        categories=("productivity",),
        description_keywords=("productivity", "workflow", "tips"),
        daily_posts=200,
        avg_comment_length=100,
        cache_hit_rate=0.9,
    )
    unrelated = CommunityProfile(
        name="r/gaming",
        categories=("gaming",),
        description_keywords=("gaming", "esports"),
        daily_posts=200,
        avg_comment_length=100,
        cache_hit_rate=0.4,
    )

    scores = _score_communities(keywords, [relevant, unrelated])
    assert scores[relevant] > scores[unrelated]


def test_description_match_uses_cosine_similarity() -> None:
    keywords = KeywordExtractionResult(
        keywords=["machine learning", "automation", "workflow"],
        weights={"machine learning": 1.0, "automation": 0.9, "workflow": 0.7},
        total_keywords=3,
    )

    close_match = _calculate_description_match(
        keywords,
        ["machine", "learning", "workflow"],
    )
    distant_match = _calculate_description_match(
        keywords,
        ["cooking", "recipes", "baking"],
    )
    assert close_match > distant_match
    assert 0.0 <= close_match <= 1.0


def test_select_diverse_top_k_honours_category_cap() -> None:
    scored: Dict[CommunityProfile, float] = {
        CommunityProfile(
            name=f"r/tech{i}",
            categories=("tech",),
            description_keywords=("ai", "ml"),
            daily_posts=150,
            avg_comment_length=90,
            cache_hit_rate=0.7,
        ): 0.9 - (i * 0.01)
        for i in range(8)
    }
    business_profile = CommunityProfile(
        name="r/business",
        categories=("business",),
        description_keywords=("growth", "strategy"),
        daily_posts=120,
        avg_comment_length=85,
        cache_hit_rate=0.6,
    )
    scored[business_profile] = 0.82

    selected = _select_diverse_top_k(scored, k=6, max_per_category=3)
    tech_count = sum(1 for community in selected if "tech" in community.categories)
    assert tech_count <= 3
    assert any("business" in community.categories for community in selected)


def test_fallback_overlap_when_tfidf_fails() -> None:
    keywords = KeywordExtractionResult(
        keywords=["ai"],
        weights={"ai": 1.0},
        total_keywords=1,
    )
    community_keywords: Sequence[str] = ()
    assert _fallback_description_overlap(keywords.weights, community_keywords) == 0.0


async def test_discover_communities_invalid_input() -> None:
    with pytest.raises(ValueError):
        await discover_communities("")


def test_calculate_target_communities_modes() -> None:
    assert _calculate_target_communities(0.85) == 30
    assert _calculate_target_communities(0.7) == 20
    assert _calculate_target_communities(0.4) == 10
