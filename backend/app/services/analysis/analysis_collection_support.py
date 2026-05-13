from __future__ import annotations

import logging
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any, Dict, List, Sequence

from sqlalchemy import case, select, text

from app.core.config import Settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.community.community_roles import communities_for_role
from app.services.crawl.data_collection import CollectionResult, DataCollectionService
from app.services.infrastructure.cache_manager import CacheManager
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.services.discovery.warzone_classifier import WarzoneClassifier
from app.services.mock.demo_data_provider import generate_demo_posts

logger = logging.getLogger(__name__)

CACHE_HIT_RATE_TARGET: float = 0.9
_OPEN_TOPIC_WARZONE_MIN_GAP: float = 0.12


class InsufficientDataError(RuntimeError):
    """Raised when real data is insufficient and mock fallback is disallowed."""


@dataclass(frozen=True)
class CommunityProfile:
    name: str
    categories: Sequence[str]
    description_keywords: Sequence[str]
    daily_posts: int
    avg_comment_length: int
    cache_hit_rate: float


@dataclass(frozen=True)
class OpenTopicRoute:
    warzone: str
    confidence: float
    reasons: Sequence[str]
    seed_profiles: Sequence[CommunityProfile]
    allowed_names: frozenset[str]
    margin: float = 1.0
    candidate_warzones: Sequence[str] = ()


@dataclass(frozen=True)
class CollectedCommunity:
    profile: CommunityProfile
    posts: List[Dict[str, Any]]
    cache_hits: int
    cache_misses: int


def normalise_community_name(raw: str) -> str:
    """Ensure name is in r/<slug> lower-case format."""
    name = (raw or "").strip()
    if not name:
        return "r/unknown"
    if name.lower().startswith("r/"):
        name = name[2:]
    name = name.lstrip("/")
    return f"r/{name.lower()}"


def group_search_posts_by_selected_subreddit(
    *,
    search_posts: Sequence[RedditPost],
    selected: Sequence[CommunityProfile],
) -> Dict[str, List[RedditPost]]:
    selected_names = {normalise_community_name(profile.name) for profile in selected}
    grouped: Dict[str, List[RedditPost]] = {}
    for post in search_posts:
        name = normalise_community_name(getattr(post, "subreddit", ""))
        if name == "r/unknown":
            continue
        if name not in selected_names:
            continue
        grouped.setdefault(name, []).append(post)
    return grouped


COMMUNITY_CATALOGUE: List[CommunityProfile] = [
    CommunityProfile(
        name="r/startups",
        categories=("startup", "business", "founder"),
        description_keywords=("startup", "founder", "product", "launch"),
        daily_posts=180,
        avg_comment_length=72,
        cache_hit_rate=0.91,
    ),
    CommunityProfile(
        name="r/Entrepreneur",
        categories=("business", "marketing", "sales"),
        description_keywords=("marketing", "sales", "pitch", "growth"),
        daily_posts=150,
        avg_comment_length=64,
        cache_hit_rate=0.88,
    ),
    CommunityProfile(
        name="r/ProductManagement",
        categories=("product", "ux", "research"),
        description_keywords=("roadmap", "user", "feedback", "discovery"),
        daily_posts=95,
        avg_comment_length=90,
        cache_hit_rate=0.75,
    ),
    CommunityProfile(
        name="r/SaaS",
        categories=("saas", "pricing", "metrics"),
        description_keywords=("subscription", "pricing", "mrr", "expansion"),
        daily_posts=65,
        avg_comment_length=84,
        cache_hit_rate=0.8,
    ),
    CommunityProfile(
        name="r/marketing",
        categories=("marketing", "brand", "campaign"),
        description_keywords=("campaign", "seo", "brand", "acquisition"),
        daily_posts=210,
        avg_comment_length=58,
        cache_hit_rate=0.67,
    ),
    CommunityProfile(
        name="r/technology",
        categories=("tech", "ai", "tools"),
        description_keywords=("ai", "machine", "automation", "cloud"),
        daily_posts=320,
        avg_comment_length=42,
        cache_hit_rate=0.62,
    ),
    CommunityProfile(
        name="r/artificial",
        categories=("ai", "ml", "research"),
        description_keywords=("ai", "nlp", "ml", "model"),
        daily_posts=140,
        avg_comment_length=110,
        cache_hit_rate=0.71,
    ),
    CommunityProfile(
        name="r/userexperience",
        categories=("ux", "design", "research"),
        description_keywords=("ux", "interview", "journey", "pain"),
        daily_posts=60,
        avg_comment_length=78,
        cache_hit_rate=0.74,
    ),
    CommunityProfile(
        name="r/smallbusiness",
        categories=("smb", "operations"),
        description_keywords=("small", "inventory", "operations", "cashflow"),
        daily_posts=55,
        avg_comment_length=66,
        cache_hit_rate=0.69,
    ),
    CommunityProfile(
        name="r/GrowthHacking",
        categories=("growth", "metrics", "funnels"),
        description_keywords=("growth", "funnel", "retention", "activation"),
        daily_posts=82,
        avg_comment_length=61,
        cache_hit_rate=0.64,
    ),
    CommunityProfile(
        name="r/CryptoCurrency",
        categories=("crypto", "blockchain", "trading"),
        description_keywords=("crypto", "bitcoin", "ethereum", "blockchain", "trading", "defi"),
        daily_posts=500,
        avg_comment_length=65,
        cache_hit_rate=0.75,
    ),
    CommunityProfile(
        name="r/Bitcoin",
        categories=("crypto", "bitcoin", "investment"),
        description_keywords=("bitcoin", "btc", "mining", "wallet", "hodl"),
        daily_posts=350,
        avg_comment_length=58,
        cache_hit_rate=0.78,
    ),
    CommunityProfile(
        name="r/ethereum",
        categories=("crypto", "ethereum", "defi"),
        description_keywords=("ethereum", "eth", "smart contract", "defi", "nft"),
        daily_posts=280,
        avg_comment_length=72,
        cache_hit_rate=0.76,
    ),
    CommunityProfile(
        name="r/CryptoMarkets",
        categories=("crypto", "trading", "market"),
        description_keywords=("crypto", "trading", "market", "analysis", "price"),
        daily_posts=220,
        avg_comment_length=55,
        cache_hit_rate=0.72,
    ),
    CommunityProfile(
        name="r/stocks",
        categories=("stocks", "investing", "trading"),
        description_keywords=("stocks", "shares", "trading", "market", "portfolio"),
        daily_posts=400,
        avg_comment_length=68,
        cache_hit_rate=0.80,
    ),
    CommunityProfile(
        name="r/investing",
        categories=("investing", "finance", "portfolio"),
        description_keywords=("investing", "portfolio", "dividend", "etf", "retirement"),
        daily_posts=320,
        avg_comment_length=75,
        cache_hit_rate=0.82,
    ),
    CommunityProfile(
        name="r/StockMarket",
        categories=("stocks", "market", "trading"),
        description_keywords=("stock", "market", "trading", "analysis", "earnings"),
        daily_posts=250,
        avg_comment_length=62,
        cache_hit_rate=0.77,
    ),
    CommunityProfile(
        name="r/wallstreetbets",
        categories=("stocks", "trading", "options"),
        description_keywords=("stocks", "options", "yolo", "trading", "calls", "puts"),
        daily_posts=800,
        avg_comment_length=45,
        cache_hit_rate=0.68,
    ),
    CommunityProfile(
        name="r/personalfinance",
        categories=("finance", "budgeting", "savings"),
        description_keywords=("finance", "budget", "savings", "debt", "credit"),
        daily_posts=450,
        avg_comment_length=85,
        cache_hit_rate=0.84,
    ),
    CommunityProfile(
        name="r/financialindependence",
        categories=("finance", "fire", "investing"),
        description_keywords=("fire", "retirement", "investing", "savings", "passive income"),
        daily_posts=180,
        avg_comment_length=95,
        cache_hit_rate=0.81,
    ),
]

_OPEN_TOPIC_WARZONE_MIN_CONFIDENCE = 0.45

_WARZONE_COMMUNITY_SEEDS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "Ecommerce_Business": (
        ("r/ecommerce", ("ecommerce", "shopify", "conversion", "store")),
        ("r/shopify", ("shopify", "checkout", "payments", "plugin")),
        ("r/dropshipping", ("dropshipping", "fulfillment", "supplier", "ads")),
        ("r/startups", ("startup", "founder", "saas", "product")),
        ("r/smallbusiness", ("small business", "operations", "cashflow", "payments")),
        ("r/SaaS", ("saas", "subscription", "pricing", "mrr")),
    ),
    "Home_Lifestyle": (
        ("r/homeowners", ("home", "house", "maintenance", "cleaning")),
        ("r/CleaningTips", ("cleaning", "vacuum", "dust", "organization")),
        ("r/declutter", ("declutter", "storage", "organization", "space")),
        ("r/organization", ("organization", "storage", "home", "space")),
        ("r/RobotVacuums", ("robot vacuum", "vacuum", "mapping", "dust")),
        ("r/VacuumCleaners", ("vacuum", "cleaning", "pet hair", "dust")),
    ),
    "Tools_EDC": (
        ("r/EDC", ("edc", "carry", "pocket", "organizer")),
        ("r/flashlight", ("flashlight", "clip", "battery", "beam")),
        ("r/knifeclub", ("knife", "blade", "carry", "clip")),
        ("r/multitools", ("multitool", "pliers", "carry", "tool")),
        ("r/Tools", ("tools", "wrench", "drill", "kit")),
    ),
    "AI_Workflow": (
        ("r/ChatGPT", ("chatgpt", "prompt", "workflow", "automation")),
        ("r/LocalLLaMA", ("local llm", "llama", "agent", "workflow")),
        ("r/artificial", ("ai", "llm", "automation", "agent")),
        ("r/ClaudeAI", ("claude", "workflow", "prompt", "automation")),
        ("r/Notion", ("notion", "automation", "workflow", "docs")),
    ),
    "Family_Parenting": (
        ("r/parenting", ("parenting", "baby", "sleep", "feeding")),
        ("r/NewParents", ("new parent", "baby", "feeding", "sleep")),
        ("r/BabyBumps", ("baby", "newborn", "feeding", "schedule")),
        ("r/beyondthebump", ("newborn", "sleep", "routine", "baby")),
        ("r/daddit", ("dad", "baby", "parenting", "routine")),
    ),
    "Food_Coffee_Lifestyle": (
        ("r/espresso", ("espresso", "grinder", "dial in", "shot")),
        ("r/Coffee", ("coffee", "brew", "grinder", "beans")),
        ("r/pourover", ("pourover", "brew", "filter", "coffee")),
        ("r/superautomatic", ("superautomatic", "espresso", "milk", "machine")),
        ("r/nespresso", ("nespresso", "capsule", "coffee", "machine")),
    ),
    "Minimal_Outdoor": (
        ("r/onebag", ("onebag", "travel", "packing", "backpack")),
        ("r/Ultralight", ("ultralight", "camping", "hiking", "gear")),
        ("r/CampingGear", ("camping", "gear", "pack", "outdoor")),
        ("r/ManyBaggers", ("bag", "organizer", "carry", "travel")),
        ("r/CampingandHiking", ("camping", "hiking", "outdoor", "gear")),
    ),
    "Frugal_Living": (
        ("r/frugal", ("frugal", "budget", "save money", "subscription")),
        ("r/ynab", ("budget", "subscription", "bill", "spending")),
        ("r/povertyfinance", ("budget", "bills", "cost", "save money")),
        ("r/nobuy", ("nobuy", "spending", "subscription", "budget")),
        ("r/personalfinance", ("budget", "bill", "subscription", "debt")),
    ),
}


@lru_cache(maxsize=1)
def _get_warzone_classifier() -> WarzoneClassifier:
    config_path = Path(__file__).resolve().parents[3] / "config" / "warzones.yaml"
    return WarzoneClassifier(config_path)


def _build_seed_profile(
    warzone: str, community_name: str, keywords: Sequence[str]
) -> CommunityProfile:
    return CommunityProfile(
        name=community_name,
        categories=("seed", f"warzone:{warzone}"),
        description_keywords=tuple(keywords),
        daily_posts=80,
        avg_comment_length=72,
        cache_hit_rate=0.55,
    )


@lru_cache(maxsize=32)
def _build_open_topic_route_from_text(route_text: str) ->Optional[ OpenTopicRoute]:
    classifier = _get_warzone_classifier()
    candidates = classifier.classify_ranked_texts([route_text], limit=3)
    if not candidates:
        return None
    best = candidates[0]
    if not best.warzone or best.warzone == "unknown":
        return None
    if float(best.confidence) < _OPEN_TOPIC_WARZONE_MIN_CONFIDENCE:
        return None
    margin = float(best.confidence)
    if len(candidates) > 1:
        second = candidates[1]
        margin = round(float(best.confidence) - float(second.confidence), 3)
        if margin < _OPEN_TOPIC_WARZONE_MIN_GAP:
            return None

    seeds = tuple(
        _build_seed_profile(best.warzone, community_name, seed_keywords)
        for community_name, seed_keywords in _WARZONE_COMMUNITY_SEEDS.get(best.warzone, ())
    )
    allowed_names = frozenset(
        normalise_community_name(profile.name) for profile in seeds if profile.name
    )
    return OpenTopicRoute(
        warzone=best.warzone,
        confidence=float(best.confidence),
        reasons=tuple(best.reasons),
        seed_profiles=seeds,
        allowed_names=allowed_names,
        margin=margin,
        candidate_warzones=tuple(candidate.warzone for candidate in candidates),
    )


def build_open_topic_route(
    product_description: str,
    keywords: Sequence[str],
    route_query:Optional[ str] = None,
) ->Optional[ OpenTopicRoute]:
    route_text = "\n".join(
        part.strip()
        for part in [
            product_description,
            route_query or "",
            "" if route_query else " ".join(str(k) for k in keywords if k),
        ]
        if part and part.strip()
    )
    if not route_text:
        return None
    return _build_open_topic_route_from_text(route_text)


@lru_cache(maxsize=512)
def _classify_community_warzone(
    community_name: str, categories: tuple[str, ...], description_keywords: tuple[str, ...]
) -> str:
    explicit = next(
        (
            cat.split("warzone:", 1)[1]
            for cat in categories
            if isinstance(cat, str) and cat.startswith("warzone:")
        ),
        "",
    )
    if explicit:
        return explicit
    guess = _get_warzone_classifier().classify_texts(
        [community_name, " ".join(categories), " ".join(description_keywords)]
    )
    if not guess.warzone or guess.warzone == "unknown":
        return ""
    return str(guess.warzone)


def _profile_matches_open_topic_route(
    profile: CommunityProfile, route:Optional[ OpenTopicRoute]
) -> bool:
    if route is None:
        return True
    normalized = normalise_community_name(profile.name)
    if normalized in route.allowed_names:
        return True
    explicit_warzone = next(
        (
            str(cat).split("warzone:", 1)[1]
            for cat in profile.categories
            if isinstance(cat, str) and str(cat).startswith("warzone:")
        ),
        "",
    )
    return explicit_warzone == route.warzone


def filter_communities_for_open_topic_route(
    communities: Sequence[CommunityProfile], route:Optional[ OpenTopicRoute]
) -> list[CommunityProfile]:
    if route is None:
        return list(communities)
    filtered = [
        community
        for community in communities
        if _profile_matches_open_topic_route(community, route)
    ]
    seed_names = {normalise_community_name(profile.name) for profile in filtered}
    for seed in route.seed_profiles:
        normalized = normalise_community_name(seed.name)
        if normalized not in seed_names:
            filtered.append(seed)
            seed_names.add(normalized)
    return filtered


def open_topic_route_allows_name(name: str, route:Optional[ OpenTopicRoute]) -> bool:
    if route is None:
        return True
    normalized = normalise_community_name(name)
    return normalized in route.allowed_names


def score_community(keywords: Sequence[str], profile: CommunityProfile) -> float:
    if not keywords:
        keyword_score = 0.0
    else:
        overlap = len(set(keywords) & set(profile.description_keywords))
        keyword_score = overlap / len(keywords)

    activity_score = min(profile.daily_posts / 200, 1.0)
    quality_score = min(profile.avg_comment_length / 120, 1.0)
    return keyword_score * 0.4 + activity_score * 0.3 + quality_score * 0.3


def normalise_cache_hit_rate(hit_rate: float) -> float:
    return min(max(hit_rate, CACHE_HIT_RATE_TARGET), 1.0)


def build_collection_warnings(
    stale_cache_subreddits: Sequence[str],
    stale_cache_fallback_subreddits: Sequence[str],
    api_failures: Sequence[dict[str, str]],
) -> list[str]:
    warnings: list[str] = []
    if stale_cache_subreddits:
        warnings.append("stale_cache_detected")
    if stale_cache_fallback_subreddits:
        warnings.append("stale_cache_fallback")
    if any(item.get("reason") == "rate_limit" for item in api_failures):
        warnings.append("reddit_rate_limited")
    if any(item.get("reason") == "error" for item in api_failures):
        warnings.append("reddit_api_error")
    return warnings


async def check_trend_views_freshness() -> tuple[bool, list[str]]:
    threshold_hours = int(os.getenv("MV_STALE_THRESHOLD_HOURS", "48"))
    threshold = timedelta(hours=max(1, threshold_hours))
    task_to_view = {
        "refresh_mv_monthly_trend": "mv_monthly_trend",
        "refresh_post_comment_stats": "post_comment_stats",
    }
    stale_views: list[str] = []
    now = datetime.now(timezone.utc)

    try:
        async with SessionFactory() as session:
            for task_name, view_name in task_to_view.items():
                result = await session.execute(
                    text(
                        """
                        SELECT ended_at
                        FROM maintenance_audit
                        WHERE task_name = :task_name
                        ORDER BY ended_at DESC NULLS LAST
                        LIMIT 1
                        """
                    ),
                    {"task_name": task_name},
                )
                last_refreshed = result.scalar_one_or_none()
                if last_refreshed is None or (now - last_refreshed) > threshold:
                    stale_views.append(view_name)
    except Exception:
        logger.warning("Failed to check materialized view freshness", exc_info=True)
        return False, []

    return bool(stale_views), stale_views


async def fetch_coverage_summary(
    community_names: Sequence[str],
) -> dict[str, Any]:
    names = sorted(
        {
            normalise_community_name(name)
            for name in community_names
            if isinstance(name, str) and name.strip()
        }
    )
    if not names:
        return {
            "status_counts": {},
            "coverage_months_min": 0,
            "coverage_months_avg": 0,
            "coverage_months_max": 0,
            "capped_count": 0,
            "community_statuses": [],
            "missing_communities": [],
        }

    async with SessionFactory() as session:
        result = await session.execute(
            select(
                CommunityRegistry.community_name,
                CommunityRuntimeState.backfill_floor,
                CommunityRuntimeState.sample_posts,
                CommunityRuntimeState.sample_comments,
                CommunityRuntimeState.runtime_notes,
            )
            .join(
                CommunityRuntimeState,
                CommunityRuntimeState.community_id == CommunityRegistry.id,
            )
            .where(CommunityRegistry.community_name.in_(names))
        )
        rows = list(result.mappings())

    status_counts: Counter[str] = Counter()
    coverage_values: list[int] = []
    capped_count = 0
    community_statuses: list[dict[str, Any]] = []
    found_names: set[str] = set()

    for row in rows:
        name = str(row.get("community_name") or "").strip()
        if not name:
            continue
        found_names.add(name)
        notes = row.get("runtime_notes") or {}
        if not isinstance(notes, dict):
            notes = {}
        status = str(notes.get("backfill_status") or "unknown").strip() or "unknown"
        status_counts[status] += 1
        coverage = notes.get("coverage_months")
        if isinstance(coverage, int):
            coverage_values.append(coverage)
        capped = bool(notes.get("backfill_capped") or False)
        if capped or status == "DONE_CAPPED":
            capped_count += 1
        community_statuses.append(
            {
                "community": name,
                "backfill_status": status,
                "coverage_months": int(coverage or 0),
                "sample_posts": int(row.get("sample_posts") or 0),
                "sample_comments": int(row.get("sample_comments") or 0),
                "backfill_capped": capped,
            }
        )

    missing = sorted(set(names) - found_names)
    if coverage_values:
        coverage_min = min(coverage_values)
        coverage_max = max(coverage_values)
        coverage_avg = round(sum(coverage_values) / len(coverage_values), 2)
    else:
        coverage_min = 0
        coverage_max = 0
        coverage_avg = 0

    return {
        "status_counts": dict(status_counts),
        "coverage_months_min": coverage_min,
        "coverage_months_avg": coverage_avg,
        "coverage_months_max": coverage_max,
        "capped_count": capped_count,
        "community_statuses": community_statuses,
        "missing_communities": missing,
    }


def community_pool_priority_order(model: type[CommunityPool]) -> Any:
    return case(
        (model.priority == "high", 3),
        (model.priority == "medium", 2),
        (model.priority == "low", 1),
        else_=0,
    )


def _determine_target_count(avg_cache_hit: float) -> int:
    if avg_cache_hit >= 0.8:
        return 30
    if avg_cache_hit >= 0.6:
        return 20
    return 10


def select_top_communities(keywords: Sequence[str]) -> List[CommunityProfile]:
    scored = [
        (profile, score_community(keywords, profile))
        for profile in COMMUNITY_CATALOGUE
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    initial = [item[0] for item in scored[:20]]

    if not initial:
        return []

    avg_hit = sum(normalise_cache_hit_rate(p.cache_hit_rate) for p in initial) / len(initial)
    target_count = _determine_target_count(avg_hit)
    selected: List[CommunityProfile] = []
    category_counts: Counter[str] = Counter()

    for profile in initial:
        if len(selected) >= target_count:
            break
        if any(category_counts[cat] >= 5 for cat in profile.categories):
            continue
        selected.append(profile)
        for cat in profile.categories:
            category_counts[cat] += 1

    return selected


def filter_communities_by_mode(
    communities: Sequence[CommunityProfile],
    mode: str,
) -> List[CommunityProfile]:
    mode_key = (mode or "market_insight").strip().lower()
    ops = communities_for_role("operations")
    if not ops:
        if mode_key == "operations":
            raise InsufficientDataError(
                "Operations mode requires config/community_roles.yaml roles.operations.communities"
            )
        return list(communities)

    if mode_key == "operations":
        return [c for c in communities if normalise_community_name(c.name) in ops]

    return [c for c in communities if normalise_community_name(c.name) not in ops]


def collect_data(
    communities: Sequence[CommunityProfile], keywords: Sequence[str]
) -> List[CollectedCommunity]:
    collected: List[CollectedCommunity] = []
    for profile in communities:
        posts = generate_demo_posts(profile, keywords)
        total_posts = len(posts)
        effective_hit_rate = normalise_cache_hit_rate(profile.cache_hit_rate)
        cache_hits = min(total_posts, math.ceil(total_posts * effective_hit_rate))
        cache_misses = total_posts - cache_hits
        collected.append(
            CollectedCommunity(
                profile=profile,
                posts=posts,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
            )
        )
    return collected


def backfill_cache_misses(
    entries: Sequence[CollectedCommunity],
    keywords: Sequence[str],
) -> List[CollectedCommunity]:
    if not entries:
        return []

    supplemented: List[CollectedCommunity] = []
    for entry in entries:
        if entry.posts:
            supplemented.append(entry)
            continue
        synthetic_entry = collect_data([entry.profile], keywords)[0]
        supplemented.append(synthetic_entry)
    return supplemented


def build_data_collection_service(settings: Settings) ->Optional[ DataCollectionService]:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        logger.warning(
            "Reddit credentials missing (client_id=%s, client_secret=%s). "
            "Will attempt cache-only collection or fallback to synthetic data.",
            "present" if settings.reddit_client_id else "missing",
            "present" if settings.reddit_client_secret else "missing",
        )
        return None

    reddit_client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    )
    cache_manager = CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )
    return DataCollectionService(reddit_client, cache_manager)


def collection_from_result(
    profiles: Sequence[CommunityProfile],
    result: CollectionResult,
) -> tuple[List[CollectedCommunity], int, int, int]:
    collected: List[CollectedCommunity] = []
    total_cache_hits = 0
    total_cache_misses = 0
    total_posts = 0
    for profile in profiles:
        canonical_name = normalise_community_name(profile.name)
        posts = result.posts_by_subreddit.get(canonical_name)
        if posts is None:
            posts = result.posts_by_subreddit.get(profile.name, [])
        payload = []
        for post in posts:
            normalised = reddit_post_to_dict(post)
            if normalised:
                payload.append(normalised)
        came_from_cache = (
            canonical_name in result.cached_subreddits or profile.name in result.cached_subreddits
        )
        hits = len(payload) if came_from_cache else 0
        misses = 0 if came_from_cache else len(payload)
        total_cache_hits += hits
        total_cache_misses += misses
        total_posts += len(payload)
        collected.append(
            CollectedCommunity(
                profile=profile,
                posts=payload,
                cache_hits=hits,
                cache_misses=misses,
            )
        )
    return collected, total_cache_hits, total_cache_misses, total_posts


async def try_cache_only_collection(
    profiles: Sequence[CommunityProfile],
    settings: Settings,
    cache_manager:Optional[ CacheManager] = None,
) ->Optional[ CollectionResult]:
    logger.info(f"[缓存优先] 尝试从缓存读取 {len(profiles)} 个社区")
    cache = cache_manager or CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )
    logger.info(f"[缓存优先] Redis URL: {settings.reddit_cache_redis_url}")

    posts_by_subreddit: Dict[str, List[RedditPost]] = {}
    cached_subreddits: set[str] = set()

    for profile in profiles:
        posts = await cache.get_cached_posts(profile.name)
        if posts:
            logger.info(f"[缓存优先] ✅ 缓存命中: {profile.name} ({len(posts)}个帖子)")
            posts_by_subreddit[profile.name] = posts
            cached_subreddits.add(profile.name)
        else:
            logger.warning(f"[缓存优先] ❌ 缓存未命中: {profile.name}")

    logger.info(f"[缓存优先] 缓存读取结果: {len(posts_by_subreddit)}/{len(profiles)} 个社区")

    if not posts_by_subreddit:
        logger.warning(
            "[降级策略] 所有社区缓存未命中 (checked %d communities). "
            "Reddit credentials unavailable. Falling back to synthetic data.",
            len(profiles),
        )
        return None

    total_posts = sum(len(posts) for posts in posts_by_subreddit.values())
    cache_hit_rate = len(cached_subreddits) / max(len(profiles), 1)

    return CollectionResult(
        total_posts=total_posts,
        cache_hits=len(cached_subreddits),
        api_calls=0,
        cache_hit_rate=cache_hit_rate,
        posts_by_subreddit=posts_by_subreddit,
        cached_subreddits=cached_subreddits,
    )


def reddit_post_to_dict(post: Any) -> Dict[str, Any]:
    if post is None:
        return {}

    if isinstance(post, (list, tuple)):
        for item in post:
            normalised = reddit_post_to_dict(item)
            if normalised:
                return normalised
        return {}

    if isinstance(post, dict):
        title = str(post.get("title", "") or "")
        selftext = str(post.get("selftext", "") or post.get("summary", "") or "")
        summary_source = (selftext or title).strip()
        summary = f"{summary_source[:197]}..." if len(summary_source) > 200 else summary_source
        return {
            "id": str(post.get("id", "")),
            "title": title,
            "summary": summary,
            "selftext": selftext,
            "body": selftext,
            "score": int(post.get("score", 0) or 0),
            "num_comments": int(post.get("num_comments", 0) or 0),
            "url": str(post.get("url", "") or ""),
            "permalink": str(post.get("permalink", "") or post.get("url", "") or ""),
            "author": str(post.get("author", "") or ""),
            "subreddit": str(post.get("subreddit", "") or ""),
        }

    try:
        title = str(getattr(post, "title", "") or "")
        selftext = str(getattr(post, "selftext", "") or "")
        score = int(getattr(post, "score", 0) or 0)
        num_comments = int(getattr(post, "num_comments", 0) or 0)
        url = str(getattr(post, "url", "") or "")
        permalink = str(getattr(post, "permalink", "") or url)
        author = str(getattr(post, "author", "") or "")
        subreddit = str(getattr(post, "subreddit", "") or "")

        summary_source = (selftext or title).strip()
        summary = f"{summary_source[:197]}..." if len(summary_source) > 200 else summary_source

        return {
            "id": str(getattr(post, "id", "") or getattr(post, "source_post_id", "")),
            "title": title,
            "summary": summary,
            "selftext": selftext,
            "body": selftext,
            "score": score,
            "num_comments": num_comments,
            "url": url,
            "permalink": permalink,
            "author": author,
            "subreddit": subreddit,
        }
    except AttributeError:
        return {}
    except Exception:
        return {}


__all__ = [
    "CACHE_HIT_RATE_TARGET",
    "COMMUNITY_CATALOGUE",
    "CollectedCommunity",
    "CommunityProfile",
    "InsufficientDataError",
    "OpenTopicRoute",
    "backfill_cache_misses",
    "build_collection_warnings",
    "build_data_collection_service",
    "build_open_topic_route",
    "check_trend_views_freshness",
    "collection_from_result",
    "collect_data",
    "community_pool_priority_order",
    "fetch_coverage_summary",
    "filter_communities_by_mode",
    "filter_communities_for_open_topic_route",
    "group_search_posts_by_selected_subreddit",
    "normalise_cache_hit_rate",
    "normalise_community_name",
    "open_topic_route_allows_name",
    "reddit_post_to_dict",
    "score_community",
    "select_top_communities",
    "try_cache_only_collection",
]
