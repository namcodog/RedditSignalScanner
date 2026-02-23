"""
Analysis engine implementation aligned with PRD-03's四步流水线。

The goal is not to provide production-grade NLP, but to honour the PRD contract:
    1. 智能社区发现（基于产品描述与社区画像的打分）
    2. 并行数据采集（模拟缓存优先策略并计算缓存命中率）
    3. 信号提取（痛点 / 竞品 / 机会）
    4. 智能排序输出（生成可信度加权的结构化报告）

The implementation uses deterministic heuristics so that automated tests
receive stable output while still reflecting the architecture laid out in
docs/PRD/PRD-03-分析引擎.md.
"""

from __future__ import annotations

import json
import logging
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import partial
from textwrap import dedent
from typing import Any, Callable, Dict, List, Optional, Sequence, Mapping

from sqlalchemy import case, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import Settings, get_settings
from app.db.session import SessionFactory
from app.models.posts_storage import PostHot, PostRaw
from app.schemas.task import TaskSummary
from app.services.analysis import sample_guard
from app.services.analysis.deduplicator import (
    DeduplicationStats,
    deduplicate_posts,
    deduplicate_posts_by_embeddings,
    get_last_stats,
)
from app.services.analysis.hybrid_retriever import fetch_hybrid_posts
from app.services.analysis.entity_matcher import EntityMatcher
from app.services.analysis.entity_pipeline import EntityPipeline
from app.services.analysis.keyword_crawler import keyword_crawl
from app.services.analysis.insights_enrichment import (
    build_battlefield_profiles,
    build_market_saturation_payload,
    build_top_drivers,
    derive_driver_label,
    summarize_trend_series,
)
from app.services.analysis.pain_cluster import cluster_pain_points
from app.services.analysis.competitor_layering import assign_competitor_layers
from app.services.analysis.opportunity_scorer import OpportunityScorer
from app.services.analysis.saturation_matrix import SaturationMatrix
from app.services.analysis.signal_extraction import (
    BusinessSignals,
    CompetitorSignal,
    OpportunitySignal,
    PainPointSignal,
    SignalExtractor,
)
from app.services.cache_manager import CacheManager
from app.services.data_collection import CollectionResult, DataCollectionService
from app.services.facts_v2.quality import quality_check_facts_v2
from app.services.facts_v2.slice import build_facts_slice_for_report
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.llm.report_prompts import (
    build_complete_report_v9,
    build_report_structured_prompt_v9,
    format_facts_for_prompt,
)
from app.services.mock.demo_data_provider import generate_demo_posts
from app.services.reddit_client import RedditAPIClient, RedditPost
from app.services.reporting.opportunity_report import build_opportunity_reports
from app.services.t1_stats import build_trend_analysis, fetch_topic_relevant_communities
from app.services.semantic.embedding_service import MODEL_NAME
from app.models.community_cache import CommunityCache
from app.models.discovered_community import DiscoveredCommunity
from app.models.community_pool import CommunityPool
from app.services.community_roles import communities_for_role
from app.services.topic_profiles import (
    TopicProfile,
    build_fetch_keywords,
    build_search_keywords,
    filter_items_by_profile_context,
    load_topic_profiles,
    match_topic_profile,
    normalize_subreddit,
    topic_profile_allows_community,
    topic_profile_blocklist_keywords,
)
from app.services.analysis.signal_lexicon import get_signal_lexicon
from app.services.blacklist_loader import get_blacklist_config

logger = logging.getLogger(__name__)

SIGNAL_EXTRACTOR = SignalExtractor()
CACHE_HIT_RATE_TARGET: float = 0.9  # PRD/PRD-03 §1.4 缓存优先：90%数据来自预缓存
MIN_SAMPLE_SIZE: int = 1500
try:
    SAMPLE_LOOKBACK_DAYS: int = max(
        1, int(os.getenv("SAMPLE_LOOKBACK_DAYS", "365"))
    )
except Exception:
    SAMPLE_LOOKBACK_DAYS = 365

# --- Facts v2: pain rollup (Phase106) ---
# 大白话：把“句子级碎片抱怨”合并成少量“痛点簇”，否则永远过不了 mentions/authors 门槛。
_PAIN_BUCKET_TITLES: dict[str, str] = {
    "cost": "太贵/成本高",
    "broken": "功能出错/不稳定",
    "slow": "太慢/效率低",
    "complex": "太复杂/不好上手",
    "blocked": "卡住了/做不到",
    "other": "其他抱怨",
}

_PAIN_BUCKET_RULES: list[tuple[str, tuple[str, ...]]] | None = None

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
    "com",
    "www",
    "http",
    "https",
}


def _get_pain_bucket_rules() -> list[tuple[str, tuple[str, ...]]]:
    global _PAIN_BUCKET_RULES
    if _PAIN_BUCKET_RULES is None:
        _PAIN_BUCKET_RULES = get_signal_lexicon().iter_pain_buckets()
    return _PAIN_BUCKET_RULES


def _bucket_pain_text(text: str) -> str:
    lowered = (text or "").lower()
    for bucket, needles in _get_pain_bucket_rules():
        if any(needle in lowered for needle in needles):
            return bucket
    return "other"


def _cluster_pain_signals_for_facts(
    pains: Sequence[PainPointSignal],
    *,
    evidence_count: Callable[[str], int],
    unique_authors: Callable[[Sequence[str]], int],
    evidence_quote_ids: Callable[[Sequence[str]], list[str]],
    max_clusters: int = 8,
) -> list[dict[str, Any]]:
    if not pains:
        return []

    def _dedupe(ids: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for sid in ids:
            key = str(sid or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    bucket_to_ids: dict[str, list[str]] = {}
    overall_ids: list[str] = []

    for pain in pains:
        desc = str(getattr(pain, "description", "") or "").strip()
        if not desc:
            continue
        src_raw = getattr(pain, "source_posts", []) or []
        src_ids = _dedupe([str(x or "").strip() for x in src_raw])
        if not src_ids:
            continue
        overall_ids.extend(src_ids)
        bucket = _bucket_pain_text(desc)
        bucket_to_ids.setdefault(bucket, []).extend(src_ids)

    overall_unique = _dedupe(overall_ids)
    if not overall_unique:
        return []

    def _mk(title: str, source_ids: Sequence[str]) -> dict[str, Any]:
        ids = _dedupe(source_ids)
        mentions = sum(int(evidence_count(sid) or 0) for sid in ids)
        # Defensive: ensure at least 1 when we have ids (avoid 0 due to bad evidence_count stubs).
        mentions = max(1, mentions) if ids else 0
        return {
            "title": title,
            "metrics": {"mentions": mentions, "unique_authors": int(unique_authors(ids) or 0)},
            "evidence_quote_ids": evidence_quote_ids(ids),
        }

    clusters: list[dict[str, Any]] = []
    clusters.append(_mk("主要抱怨（汇总）", overall_unique))

    for bucket, ids in bucket_to_ids.items():
        title = _PAIN_BUCKET_TITLES.get(bucket, bucket)
        clusters.append(_mk(title, ids))

    def _metric_int(row: Mapping[str, object], key: str) -> int:
        metrics = row.get("metrics")
        if isinstance(metrics, Mapping):
            raw = metrics.get(key)
            try:
                return int(raw or 0)
            except (TypeError, ValueError):
                return 0
        return 0

    clusters.sort(
        key=lambda row: (_metric_int(row, "mentions"), _metric_int(row, "unique_authors")),
        reverse=True,
    )
    return clusters[: max(1, int(max_clusters))]
_GUARD_SAMPLE_LIMIT: int = 2000
DATA_LINEAGE_TARGET_IDS_MAX: int = max(
    0, int(os.getenv("DATA_LINEAGE_TARGET_IDS_MAX", "200") or 200)
)
BUSINESS_POOL_WEIGHTS: dict[str, float] = {
    "core": 1.2,
    "lab": 1.0,
    "unknown": 0.9,
}
VALUE_SCORE_WEIGHT: float = 2.0
OPPORTUNITY_SCORER = OpportunityScorer()
ENTITY_MATCHER = EntityMatcher()
ENTITY_PIPELINE = EntityPipeline()

_REMEDIATION_BUDGET_REDIS: object | None = None


def _get_remediation_budget_redis(settings: Settings):
    global _REMEDIATION_BUDGET_REDIS
    if _REMEDIATION_BUDGET_REDIS is None:
        from redis.asyncio import Redis

        redis_url = os.getenv("REMEDIATION_BUDGET_REDIS_URL") or settings.reddit_cache_redis_url
        _REMEDIATION_BUDGET_REDIS = Redis.from_url(redis_url, decode_responses=True)
    return _REMEDIATION_BUDGET_REDIS


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
class CollectedCommunity:
    profile: CommunityProfile
    posts: List[Dict[str, Any]]
    cache_hits: int
    cache_misses: int


@dataclass(frozen=True)
class AnalysisResult:
    insights: Dict[str, Any]
    sources: Dict[str, Any]
    report_html: str
    action_items: List[Dict[str, Any]]
    confidence_score: float  # 置信度分数 (0.0-1.0)


def _normalize_target_ids(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if value:
            out.append(value)
    return out


def _looks_like_reddit_post_id(raw: str) -> bool:
    """
    Heuristic: only schedule comment backfill for IDs that look like real Reddit post ids.

    - Accept: base36-ish ids ("1abcde"), "t3_" prefixed ids, or numeric internal ids.
    - Reject: demo ids that contain "/" or non-alnum symbols (e.g. "r/Foo-opportunity-bar").
    """
    value = str(raw or "").strip()
    if not value:
        return False
    if "/" in value:
        return False
    if value.startswith("t3_"):
        value = value[3:]
    if len(value) < 5:
        return False
    return value.isalnum()


def _truncate_target_ids(target_ids: list[str]) -> tuple[list[str], int, bool]:
    cleaned = [str(x or "").strip() for x in (target_ids or []) if str(x or "").strip()]
    total = len(cleaned)
    if DATA_LINEAGE_TARGET_IDS_MAX <= 0:
        return [], total, total > 0
    if total <= DATA_LINEAGE_TARGET_IDS_MAX:
        return cleaned, total, False
    return cleaned[:DATA_LINEAGE_TARGET_IDS_MAX], total, True


def _build_data_lineage(
    *,
    source_range: dict[str, int] | None = None,
    coverage: dict[str, Any] | None = None,
    remediation_actions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    crawler_run_ids: list[str] = []
    target_ids: list[str] = []
    target_ids_total = 0
    truncated = False

    for action in remediation_actions or []:
        if not isinstance(action, Mapping):
            continue
        rid = str(action.get("crawl_run_id") or "").strip()
        if rid and rid not in crawler_run_ids:
            crawler_run_ids.append(rid)

        ids = _normalize_target_ids(action.get("target_ids"))
        for tid in ids:
            if tid not in target_ids:
                target_ids.append(tid)

        try:
            target_ids_total += int(action.get("target_ids_total") or action.get("targets") or 0)
        except (TypeError, ValueError):
            pass
        if bool(action.get("target_ids_truncated")):
            truncated = True

    if target_ids_total and len(target_ids) < target_ids_total:
        truncated = True

    data_lineage: dict[str, Any] = {
        "crawler_run_ids": crawler_run_ids,
        "target_ids": target_ids,
        "target_ids_total": int(target_ids_total),
        "target_ids_truncated": bool(truncated),
    }
    if source_range is not None:
        data_lineage["source_range"] = source_range
    if coverage is not None:
        data_lineage["coverage"] = coverage
    return data_lineage


def _normalise_community_name(raw: str) -> str:
    """Ensure name is in r/<slug> lower-case format."""
    name = (raw or "").strip()
    if not name:
        return "r/unknown"
    if name.lower().startswith("r/"):
        name = name[2:]
    name = name.lstrip("/")
    return f"r/{name.lower()}"


def _merge_posts_by_id(
    primary: list[dict[str, Any]], extra: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not extra:
        return primary
    seen = {str(post.get("id") or "") for post in primary if post.get("id")}
    for post in extra:
        pid = str(post.get("id") or post.get("db_id") or "")
        if not pid or pid in seen:
            continue
        primary.append(post)
        seen.add(pid)
    return primary


def _parse_embedding_value(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(x) for x in value]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            try:
                payload = json.loads(raw.replace("'", "\""))
            except json.JSONDecodeError:
                return None
        if isinstance(payload, list):
            return [float(x) for x in payload]
    return None


async def _fetch_post_embeddings(
    session: Any, posts: Sequence[Dict[str, Any]]
) -> dict[str, list[float]]:
    ids: list[int] = []
    for post in posts:
        raw = post.get("db_id")
        if raw is None:
            continue
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    if not ids:
        return {}

    rows = await session.execute(
        text(
            """
            SELECT post_id, embedding
            FROM post_embeddings
            WHERE post_id = ANY(:ids)
              AND model_version = :model_version
            """
        ),
        {"ids": ids, "model_version": MODEL_NAME},
    )
    out: dict[str, list[float]] = {}
    for row in rows.mappings().all():
        post_id = row.get("post_id")
        embedding = _parse_embedding_value(row.get("embedding"))
        if post_id is None or embedding is None:
            continue
        out[str(post_id)] = embedding
    return out


def _build_knowledge_graph(
    *,
    aggregates: Mapping[str, Any] | None,
    high_value_pains: Sequence[Mapping[str, Any]],
    sample_posts_db: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    top_drivers: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    evidence_map: dict[str, dict[str, Any]] = {}

    for post in sample_posts_db:
        pid = str(post.get("id") or "").strip()
        if not pid:
            continue
        evidence_map[pid] = {
            "id": pid,
            "type": "post",
            "text": post.get("text") or post.get("summary") or post.get("title") or "",
            "url": post.get("permalink") or post.get("url") or "",
            "subreddit": post.get("subreddit") or "",
        }
    for comment in sample_comments_db:
        cid = str(comment.get("id") or "").strip()
        if not cid:
            continue
        evidence_map[cid] = {
            "id": cid,
            "type": "comment",
            "text": comment.get("text") or comment.get("body") or "",
            "url": comment.get("permalink") or "",
            "subreddit": comment.get("subreddit") or "",
        }

    pains_payload: list[dict[str, Any]] = []
    for pain in high_value_pains:
        name = str(pain.get("name") or pain.get("description") or "").strip()
        evidence_ids = [str(x) for x in (pain.get("evidence_quote_ids") or []) if x]
        pains_payload.append(
            {
                "name": name,
                "mentions": int(pain.get("mentions") or 0),
                "unique_authors": int(pain.get("unique_authors") or 0),
                "evidence_ids": evidence_ids,
                "evidence": [evidence_map[eid] for eid in evidence_ids if eid in evidence_map],
            }
        )

    drivers_payload: list[dict[str, Any]] = []
    for driver in top_drivers or []:
        drivers_payload.append(
            {
                "title": driver.get("title") or "",
                "description": driver.get("description") or driver.get("rationale") or "",
                "actions": driver.get("actions") or [],
                "source_pains": driver.get("source_pains") or [],
            }
        )

    communities_payload = []
    if aggregates and isinstance(aggregates, Mapping):
        communities_payload = list(aggregates.get("communities") or [])

    return {
        "communities": communities_payload,
        "pain_points": pains_payload,
        "drivers": drivers_payload,
        "evidence": list(evidence_map.values()),
    }


def _group_search_posts_by_selected_subreddit(
    *,
    search_posts: Sequence[RedditPost],
    selected: Sequence[CommunityProfile],
) -> Dict[str, List[RedditPost]]:
    """
    Reddit search 返回的 subreddit 可能是 "Shopify"（无 r/ 前缀、大小写混用）。

    如果直接用原值去匹配 selected（通常是 "r/shopify"），会导致：
    - search_posts 明明有结果
    - posts_by_subreddit 却变成空
    - 最终 posts_collected=0（假“样本不足”）
    """
    selected_names = {_normalise_community_name(profile.name) for profile in selected}
    grouped: Dict[str, List[RedditPost]] = {}
    for post in search_posts:
        name = _normalise_community_name(getattr(post, "subreddit", ""))
        if name == "r/unknown":
            continue
        if name not in selected_names:
            continue
        grouped.setdefault(name, []).append(post)
    return grouped


def _calculate_confidence_score(
    *,
    cache_hit_rate: float,
    posts_analyzed: int,
    communities_found: int,
    pain_points_count: int,
    competitors_count: int,
    opportunities_count: int,
) -> float:
    """
    计算分析结果的置信度分数 (0.0-1.0)

    置信度基于以下因素：
    1. 缓存命中率（40%权重）：越高越好，目标 90%
    2. 数据量（30%权重）：帖子数和社区数
    3. 洞察质量（30%权重）：痛点、竞品、机会的数量

    Args:
        cache_hit_rate: 缓存命中率 (0.0-1.0)
        posts_analyzed: 分析的帖子数量
        communities_found: 发现的社区数量
        pain_points_count: 提取的痛点数量
        competitors_count: 识别的竞品数量
        opportunities_count: 发现的机会数量

    Returns:
        置信度分数 (0.0-1.0)
    """
    # 1. 缓存命中率得分 (40%权重)
    # 目标是 90% 命中率，超过 90% 得满分
    cache_score = min(cache_hit_rate / 0.9, 1.0) * 0.4

    # 2. 数据量得分 (30%权重)
    # 帖子数：100+ 得满分
    posts_score = min(posts_analyzed / 100.0, 1.0) * 0.15
    # 社区数：10+ 得满分
    communities_score = min(communities_found / 10.0, 1.0) * 0.15
    data_score = posts_score + communities_score

    # 3. 洞察质量得分 (30%权重)
    # 痛点：10+ 得满分
    pain_points_score = min(pain_points_count / 10.0, 1.0) * 0.1
    # 竞品：5+ 得满分
    competitors_score = min(competitors_count / 5.0, 1.0) * 0.1
    # 机会：5+ 得满分
    opportunities_score = min(opportunities_count / 5.0, 1.0) * 0.1
    insights_score = pain_points_score + competitors_score + opportunities_score

    # 总分
    total_score = cache_score + data_score + insights_score

    # 确保在 0.0-1.0 范围内
    return max(0.0, min(1.0, total_score))


async def _extract_business_signals_from_labels(
    post_ids: Sequence[int],
) -> BusinessSignals | None:
    """尝试直接从 content_labels / content_entities 聚合业务信号。

    - 只做批量查询，无 N+1
    - 数据缺失/异常时返回 None，由上层回退到启发式 SignalExtractor
    """
    if not post_ids:
        return None

    numeric_post_ids: List[int] = []
    for pid in post_ids:
        try:
            numeric_post_ids.append(int(pid))
        except (TypeError, ValueError):
            continue

    if not numeric_post_ids:
        return None

    try:
        async with SessionFactory() as session:
            label_rows = await session.execute(
                text(
                    """
                    SELECT
                        category,
                        aspect,
                        COUNT(*) as count,
                        AVG(
                            CASE
                                WHEN sentiment::text ~ '^-?\\d+(\\.\\d+)?$' THEN sentiment::numeric
                                ELSE NULL
                            END
                        ) as avg_sentiment,
                        jsonb_agg(post_id) as sample_post_ids
                    FROM mv_analysis_labels
                    WHERE post_id = ANY(:post_ids)
                    GROUP BY category, aspect
                    """
                ),
                {"post_ids": numeric_post_ids},
            )
            labels = label_rows.mappings().all()

            entity_rows = await session.execute(
                text(
                    """
                    SELECT
                        entity_name,
                        COUNT(*) as mentions,
                        jsonb_agg(post_id) as sample_post_ids
                    FROM mv_analysis_entities
                    WHERE post_id = ANY(:post_ids)
                      AND entity_type = 'brand'
                    GROUP BY entity_name
                    """
                ),
                {"post_ids": numeric_post_ids},
            )
            entities = entity_rows.mappings().all()
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("Label-based signal extraction failed, fallback to heuristics: %s", exc)
        return None

    if not labels and not entities:
        return None

    pain_total = 0
    solution_total = 0
    intent_total = 0
    pain_signals: list[PainPointSignal] = []
    opportunity_signals: list[OpportunitySignal] = []
    for row in labels:
        category = str(row.get("category") or "").lower()
        aspect_raw = row.get("aspect")
        aspect = str(getattr(aspect_raw, "value", aspect_raw) or "").strip() or "general"
        aspect_lower = aspect.lower()
        count = int(row.get("count") or 0)
        avg_sentiment = float(row.get("avg_sentiment") or 0.0)
        sample_posts = [str(pid) for pid in (row.get("sample_post_ids") or [])]

        if category == "pain":
            pain_total += count
            pain_signals.append(
                PainPointSignal(
                    description=f"{aspect}相关痛点",
                    frequency=count,
                    sentiment=avg_sentiment,
                    keywords=[aspect],
                    source_posts=sample_posts,
                    relevance=1.0,
                )
            )
        elif category == "solution":
            solution_total += count
            opportunity_signals.append(
                OpportunitySignal(
                    description=f"{aspect} 相关 Feature Gap",
                    demand_score=0.65,
                    unmet_need=f"用户期待 {aspect} 方向的解决方案",
                    potential_users=max(3, count),
                    source_posts=sample_posts,
                    relevance=0.85,
                    keywords=[aspect],
                )
            )
        elif category == "intent":
            intent_total += count
            if aspect_lower.startswith("w2c"):
                opportunity_signals.append(
                    OpportunitySignal(
                        description="明确购买意向（W2C）",
                        demand_score=0.8,
                        unmet_need="用户表达了购买/选择意向",
                        potential_users=max(3, count),
                        source_posts=sample_posts,
                        relevance=0.9,
                        keywords=["w2c"],
                    )
                )

    denominator = solution_total + intent_total
    if denominator > 0:
        ps_ratio = pain_total / denominator
    else:
        ps_ratio = float(pain_total) if pain_total < 10 else 10.0

    brand_signals: list[CompetitorSignal] = []
    for row in entities:
        name = str(row.get("entity_name") or "").strip()
        if not name:
            continue
        mentions = int(row.get("mentions") or 0)
        sample_posts = [str(pid) for pid in (row.get("sample_post_ids") or [])]
        brand_signals.append(
            CompetitorSignal(
                name=name,
                mention_count=mentions,
                sentiment=0.0,
                context_snippets=[],
                source_posts=sample_posts,
                relevance=1.0,
            )
        )

    if not pain_signals and not brand_signals and not opportunity_signals:
        return None

    if not opportunity_signals and pain_signals:
        for pain in pain_signals[:3]:
            opportunity_signals.append(
                OpportunitySignal(
                    description=f"解决 {pain.description} 的改进机会",
                    demand_score=min(0.95, 0.6 + min(ps_ratio, 5) * 0.05),
                    unmet_need="用户反馈集中，亟需改进",
                    potential_users=max(3, pain.frequency),
                    source_posts=pain.source_posts[:3],
                    relevance=0.7,
                    keywords=pain.keywords,
                )
            )

    return BusinessSignals(
        pain_points=pain_signals,
        competitors=brand_signals,
        opportunities=opportunity_signals,
        ps_ratio=ps_ratio,
    )


async def _record_discovered_communities(
    task_id: Any,
    collected: Sequence[CollectedCommunity],
    keywords: Sequence[str],
) -> None:
    """
    Persist discovered communities for a task so前端/后续环节能查到。

    - 使用 name 唯一键 upsert，叠加 mention 次数
    - 自动触发 DiscoveredCommunity 的 before_insert 钩子以补充 community_pool
    """
    if not collected:
        return
    now = datetime.now(timezone.utc)
    keywords_payload = {"keywords": list(keywords)}

    async with SessionFactory() as session:
        for entry in collected:
            mention_count = len(entry.posts)
            if mention_count <= 0:
                continue
            name = _normalise_community_name(entry.profile.name)

            # 先确保 community_pool 中存在对应名称，避免 FK 失败
            pool_stmt = (
                pg_insert(CommunityPool)
                .values(
                    name=name,
                    # ⚠️ 发现出来的社区只用于“记录/待审核”，不能污染正式社区池：
                    # - tier 固定 candidate
                    # - 默认不激活（避免被巡航/分析当成正式输入）
                    # - status 固定 candidate
                    tier="candidate",
                    categories={},
                    description_keywords=keywords_payload,
                    daily_posts=entry.profile.daily_posts,
                    avg_comment_length=entry.profile.avg_comment_length,
                    quality_score=0.50,
                    priority="medium",
                    user_feedback_count=0,
                    discovered_count=mention_count,
                    is_active=False,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(index_elements=[CommunityPool.name])
            )
            await session.execute(pool_stmt)

            stmt = (
                pg_insert(DiscoveredCommunity)
                .values(
                    name=name,
                    discovered_from_keywords=keywords_payload,
                    discovered_count=mention_count,
                    first_discovered_at=now,
                    last_discovered_at=now,
                    status="pending",
                    discovered_from_task_id=task_id,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[DiscoveredCommunity.name],
                    set_={
                        "discovered_count": DiscoveredCommunity.discovered_count + mention_count,
                        "last_discovered_at": now,
                        "discovered_from_task_id": task_id,
                        "updated_at": now,
                        "discovered_from_keywords": keywords_payload,
                    },
                )
            )
            await session.execute(stmt)
        await session.commit()


async def _fetch_hot_samples(
    *,
    lookback_days: int,
    keywords: Sequence[str] | None = None,
) -> List[Dict[str, Any]]:
    """Load recent posts from the hot cache for sample guard checks."""
    del keywords  # Keyword filtering handled downstream if needed
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    async with SessionFactory() as session:
        result = await session.execute(
            select(PostHot)
            .where(PostHot.created_at >= since)
            .order_by(PostHot.created_at.desc())
            .limit(_GUARD_SAMPLE_LIMIT)
        )
        records = list(result.scalars())

    return [
        {
            "id": record.source_post_id,
            "title": record.title or "",
            "summary": record.body or "",
            "score": int(record.score or 0),
            "num_comments": int(record.num_comments or 0),
            "subreddit": record.subreddit or "",
            "source_type": "hot",
            "created_at": record.created_at.isoformat() if record.created_at else "",
        }
        for record in records
    ]


async def _fetch_cold_samples(
    *,
    lookback_days: int,
    keywords: Sequence[str] | None = None,
) -> List[Dict[str, Any]]:
    """Load recent posts from the cold archive for sample guard checks."""
    del keywords
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    async with SessionFactory() as session:
        result = await session.execute(
            select(PostRaw)
            .where(PostRaw.created_at >= since, PostRaw.is_current.is_(True))
            .order_by(PostRaw.created_at.desc())
            .limit(_GUARD_SAMPLE_LIMIT)
        )
        records = list(result.scalars())

    return [
        {
            "id": record.source_post_id,
            "title": record.title or "",
            "summary": record.body or "",
            "score": int(record.score or 0),
            "num_comments": int(record.num_comments or 0),
            "subreddit": record.subreddit or "",
            "source_type": "cold",
            "created_at": record.created_at.isoformat() if record.created_at else "",
        }
        for record in records
    ]


async def _supplement_samples(
    *,
    product_description: str,
    keywords: Sequence[str],
    shortfall: int,
    lookback_days: int,
) -> List[Dict[str, Any]]:
    """
    Perform keyword-based crawl to supplement sample shortfall and persist to cold storage.
    """
    time_filter = "month"
    if int(lookback_days) >= 540:  # ~18 months
        time_filter = "all"
    elif int(lookback_days) >= 365:
        time_filter = "year"
    settings = get_settings()
    if not settings.enable_reddit_search:
        logger.info("Keyword supplement disabled via ENABLE_REDDIT_SEARCH flag.")
        return []

    if not (settings.reddit_client_id and settings.reddit_client_secret):
        logger.warning(
            "Keyword supplement requested but Reddit credentials are missing."
        )
        return []

    per_query_limit = min(50, max(shortfall, 25))
    query_variants = 3 if shortfall >= 100 else 2

    try:
        reddit_client = RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            rate_limit=min(30, settings.reddit_rate_limit),
            rate_limit_window=settings.reddit_rate_limit_window_seconds,
            request_timeout=min(20.0, settings.reddit_request_timeout_seconds),
            max_concurrency=max(1, settings.reddit_max_concurrency // 2),
        )
    except Exception as exc:
        logger.warning("Failed to initialise Reddit search client: %s", exc)
        return []

    try:
        async with reddit_client as client:
            search_results = await keyword_crawl(
                client,
                product_description=product_description,
                base_keywords=keywords,
                per_query_limit=per_query_limit,
                query_variants=max(1, query_variants),
                time_filter=time_filter,
                sort="relevance",
            )
    except Exception as exc:
        logger.warning("Keyword crawl failed: %s", exc)
        return []

    if not search_results:
        return []

    supplement_posts = search_results[: max(0, shortfall)]
    now = datetime.now(timezone.utc)

    async with SessionFactory() as session:
        # posts_raw requires community_id (FK + NOT NULL). Only persist posts for communities present in pool.
        from app.models.community_pool import CommunityPool as CommunityPoolModel
        from app.utils.subreddit import subreddit_key

        subreddits = [
            subreddit_key(str(post.get("subreddit") or ""))
            for post in supplement_posts
            if str(post.get("subreddit") or "").strip()
        ]
        community_id_map: dict[str, int] = {}
        if subreddits:
            result = await session.execute(
                select(CommunityPoolModel.id, CommunityPoolModel.name).where(
                    CommunityPoolModel.name.in_(sorted(set(subreddits)))
                )
            )
            for row in result.all():
                community_id_map[str(row.name)] = int(row.id)

        rows: List[dict[str, Any]] = []
        kept_posts: List[dict[str, Any]] = []
        author_rows: list[dict[str, Any]] = []
        seen_authors: set[str] = set()
        for post in supplement_posts:
            post_id = str(post.get("id") or "").strip()
            subreddit = subreddit_key(str(post.get("subreddit") or ""))
            if not post_id or not subreddit:
                continue
            community_id = community_id_map.get(subreddit)
            if not community_id:
                continue

            created_utc = post.get("created_utc")
            created_at: datetime
            if created_utc is not None:
                try:
                    created_at = datetime.fromtimestamp(
                        float(str(created_utc)), tz=timezone.utc
                    )
                except (TypeError, ValueError):
                    created_at = now
            else:
                created_at = now

            author = str(post.get("author") or "unknown")
            metadata = {
                "source_type": "search",
                "search_keywords": list(keywords),
                "permalink": post.get("permalink"),
                "supplemented_at": now.isoformat(),
            }

            score_val = post.get("score", 0)
            num_comments_val = post.get("num_comments", 0)

            score_int: int = 0
            if score_val is not None:
                try:
                    score_int = int(str(score_val))
                except (TypeError, ValueError):
                    score_int = 0

            num_comments_int: int = 0
            if num_comments_val is not None:
                try:
                    num_comments_int = int(str(num_comments_val))
                except (TypeError, ValueError):
                    num_comments_int = 0

            row: dict[Any, Any] = {
                "source": "reddit",
                "source_post_id": post_id,
                "version": 1,
                "created_at": created_at,
                "fetched_at": now,
                "author_id": author,
                "author_name": author,
                "title": post.get("title", ""),
                "body": post.get("summary", ""),
                "url": post.get("url"),
                "subreddit": subreddit,
                "community_id": int(community_id),
                "score": score_int,
                "num_comments": num_comments_int,
            }
            row[PostRaw.extra_data] = metadata
            rows.append(row)
            kept_posts.append(post)
            if author and author not in seen_authors:
                seen_authors.add(author)
                author_rows.append({"author_id": author, "author_name": author})

        if rows:
            if author_rows:
                from app.models.author import Author

                authors_stmt = pg_insert(Author).values(author_rows)
                authors_stmt = authors_stmt.on_conflict_do_nothing(
                    index_elements=["author_id"]
                )
                await session.execute(authors_stmt)
            stmt = pg_insert(PostRaw).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["source", "source_post_id", "version"],
                set_={
                    "title": stmt.excluded.title,
                    "body": stmt.excluded.body,
                    "score": stmt.excluded.score,
                    "num_comments": stmt.excluded.num_comments,
                    "metadata": stmt.excluded.metadata,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            await session.execute(stmt)
            await session.commit()
        # Ensure the sample guard only counts posts that were actually persisted.
        supplement_posts = kept_posts

    for post in supplement_posts:
        post.setdefault("source_type", "search")

    return supplement_posts


async def _run_sample_guard(
    keywords: Sequence[str],
    product_description: str,
    *,
    lookback_days: int,
) -> Optional[sample_guard.SampleCheckResult]:
    """Execute the sample floor check with defensive fallbacks."""
    supplement = partial(
        _supplement_samples,
        product_description=product_description,
    )
    try:
        return await sample_guard.check_sample_size(
            hot_fetcher=_fetch_hot_samples,
            cold_fetcher=_fetch_cold_samples,
            supplementer=supplement,
            keywords=keywords,
            min_samples=MIN_SAMPLE_SIZE,
            lookback_days=max(1, int(lookback_days)),
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Sample guard failed (%s); continuing with analysis.", exc)
        return None


async def _build_data_readiness_snapshot(
    *, topic_profile: TopicProfile
) -> dict[str, Any]:
    """
    Contract B: analysis preflight snapshot.

    Human goal:
    - Before we "analyze", first answer: we even have enough cached/backfilled data for this topic?
    - Only reads `community_cache` waterline fields (fast, consistent).
    """
    target_communities: list[str] = []
    target_keys: list[str] = []
    for raw in (topic_profile.allowed_communities or []):
        normalized = normalize_subreddit(str(raw or ""))
        if not normalized:
            continue
        key = normalized.removeprefix("r/").strip().lower()
        if not key:
            continue
        target_communities.append(normalized)
        target_keys.append(key)

    if not target_keys:
        return {
            "target_communities": [],
            "communities_total": 0,
            "communities_found": 0,
            "missing_communities": [],
            "status_counts": {},
            "sample_posts_total": 0,
            "sample_comments_total": 0,
            "coverage_months_min": 0,
            "coverage_months_avg": 0.0,
            "coverage_months_max": 0,
            "communities": [],
        }

    async with SessionFactory() as session:
        result = await session.execute(
            select(CommunityCache).where(CommunityCache.community_key.in_(target_keys))
        )
        rows = list(result.scalars().all())

    by_key: dict[str, CommunityCache] = {
        str(row.community_key or ""): row for row in rows if getattr(row, "community_key", None)
    }

    status_counts: Counter[str] = Counter()
    missing: list[str] = []
    details: list[dict[str, Any]] = []
    coverage_months: list[int] = []
    sample_posts_total = 0
    sample_comments_total = 0

    for key, expected in zip(target_keys, target_communities):
        row = by_key.get(key)
        if row is None:
            missing.append(expected)
            status_counts["MISSING"] += 1
            details.append(
                {
                    "community": expected,
                    "status": "MISSING",
                    "coverage_months": 0,
                    "sample_posts": 0,
                    "sample_comments": 0,
                    "last_crawled_at": None,
                }
            )
            continue

        status = str(getattr(row, "backfill_status", None) or "UNKNOWN").strip() or "UNKNOWN"
        status_counts[status] += 1
        cm = int(getattr(row, "coverage_months", 0) or 0)
        coverage_months.append(cm)
        sp = int(getattr(row, "sample_posts", 0) or 0)
        sc = int(getattr(row, "sample_comments", 0) or 0)
        sample_posts_total += sp
        sample_comments_total += sc

        last_crawled = getattr(row, "last_crawled_at", None)
        details.append(
            {
                "community": str(getattr(row, "community_name", expected) or expected),
                "status": status,
                "coverage_months": cm,
                "sample_posts": sp,
                "sample_comments": sc,
                "last_crawled_at": last_crawled.isoformat() if last_crawled else None,
            }
        )

    cm_min = min(coverage_months) if coverage_months else 0
    cm_max = max(coverage_months) if coverage_months else 0
    cm_avg = round(sum(coverage_months) / max(1, len(coverage_months)), 2) if coverage_months else 0.0

    return {
        "target_communities": target_communities,
        "communities_total": len(target_communities),
        "communities_found": len(rows),
        "missing_communities": missing,
        "status_counts": dict(status_counts),
        "sample_posts_total": int(sample_posts_total),
        "sample_comments_total": int(sample_comments_total),
        "coverage_months_min": int(cm_min),
        "coverage_months_avg": float(cm_avg),
        "coverage_months_max": int(cm_max),
        "communities": details,
    }


def _build_insufficient_sample_result(
    task: TaskSummary,
    sample_result: sample_guard.SampleCheckResult,
    *,
    lookback_days: int,
) -> AnalysisResult:
    """Compose a short-circuit AnalysisResult when sample floor is not met."""
    status_payload = {
        "hot_count": sample_result.hot_count,
        "cold_count": sample_result.cold_count,
        "combined_count": sample_result.combined_count,
        "shortfall": sample_result.shortfall,
        "remaining_shortfall": sample_result.remaining_shortfall,
        "supplemented": sample_result.supplemented,
        "supplement_posts": sample_result.supplement_posts,
        "min_required": MIN_SAMPLE_SIZE,
        "lookback_days": max(1, int(lookback_days)),
    }
    report_html = dedent(
        f"""
        <html>
          <body>
            <h1>分析暂停：样本不足</h1>
            <p>当前缓存+冷库共收集 <strong>{sample_result.combined_count}</strong> 条帖子，未达到启动分析所需的 {MIN_SAMPLE_SIZE} 条。</p>
            <p>已触发补抓流程，请稍后重新尝试。若需立即分析，可扩大关键词或延长时间范围。</p>
          </body>
        </html>
        """
    ).strip()
    sources: Dict[str, Any] = {
        "communities": [],
        "posts_analyzed": int(sample_result.combined_count),
        "comments_analyzed": 0,
        "counts_analyzed": {
            "posts": int(sample_result.combined_count),
            "comments": 0,
        },
        "counts_db": {
            # Best-effort: these samples came from hot/cold cache + optional supplement persistence.
            "posts_current": int(sample_result.combined_count),
            "comments_total": 0,
            "comments_eligible": 0,
        },
        "comments_pipeline_status": "disabled",
        "cache_hit_rate": round(
            (sample_result.hot_count / sample_result.combined_count)
            if sample_result.combined_count
            else 0.0,
            2,
        ),
        "product_description": task.product_description,
        "mode": getattr(task, "mode", "market_insight"),
        "topic_profile_id": getattr(task, "topic_profile_id", None),
        "analysis_blocked": "insufficient_samples",
        "sample_status": status_payload,
        "data_source": "insufficient",
        "lookback_days": max(1, int(lookback_days)),
        "report_tier": "C_scouting",
        "facts_v2_quality": {
            "passed": True,
            "tier": "C_scouting",
            "flags": ["insufficient_samples"],
            "metrics": {
                "source_posts": int(sample_result.combined_count),
                "source_comments": 0,
            },
        },
    }
    empty_insights: Dict[str, Any] = {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
    }
    return AnalysisResult(
        insights=empty_insights,
        sources=sources,
        report_html=report_html,
        action_items=[],
        confidence_score=0.0,  # 样本不足时置信度为 0
    )


async def _schedule_auto_backfill_for_insufficient_samples(
    *,
    task: TaskSummary,
    topic_profile: "TopicProfile | None",
) -> list[dict[str, Any]]:
    """
    Contract B (P1 最小闭环)：
    当样本不足时，系统必须“自动下单补量”，而不是只说一句话。

    当前版本先做 posts 回填（走 outbox + backfill_posts_queue_v2），避免在分析阶段直连 Reddit API。
    """
    try:
        communities = (
            list(getattr(topic_profile, "allowed_communities", []) or [])
            if topic_profile is not None
            else []
        )
        if not communities:
            return []

        import uuid
        from app.services.discovery.auto_backfill_service import (
            BACKFILL_POSTS_QUEUE,
            plan_auto_backfill_posts_targets,
        )
        from app.services.task_outbox_service import enqueue_execute_target_outbox

        def _truthy_env(name: str, default: str) -> bool:
            raw = os.getenv(name, default).strip().lower()
            return raw in {"1", "true", "yes", "y", "on"}

        def _int_env(name: str, default: int) -> int:
            raw = os.getenv(name, str(default)).strip()
            try:
                return int(raw)
            except (TypeError, ValueError):
                return int(default)

        async def _count_outbox_pending() -> int:
            try:
                async with SessionFactory() as session_outbox:
                    res = await session_outbox.execute(
                        text("SELECT COUNT(*) FROM task_outbox WHERE status = 'pending'")
                    )
                    return int(res.scalar() or 0)
            except Exception:
                return 0

        def _hour_bucket(dt: datetime) -> str:
            safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            return safe.astimezone(timezone.utc).strftime("%Y%m%d%H")

        def _day_bucket(dt: datetime) -> str:
            safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            return safe.astimezone(timezone.utc).strftime("%Y%m%d")

        def _membership_level() -> str:
            raw = str(getattr(task, "membership_level", None) or "free").strip().lower()
            return raw if raw in {"free", "pro", "enterprise"} else "free"

        def _hourly_user_budget(level: str) -> int:
            if level == "enterprise":
                return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_ENTERPRISE", 1000)
            if level == "pro":
                return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_PRO", 200)
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_FREE", 50)

        def _daily_user_budget(level: str) -> int:
            if level == "enterprise":
                return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_ENTERPRISE", 5000)
            if level == "pro":
                return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_PRO", 1000)
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_FREE", 200)

        budget_enabled = _truthy_env("REMEDIATION_BUDGET_ENABLED", "1")
        per_task_budget = max(1, _int_env("REMEDIATION_TASK_TARGET_BUDGET", 200))
        budget_task_ttl_seconds = max(
            60, _int_env("REMEDIATION_TASK_BUDGET_TTL_SECONDS", 24 * 3600)
        )
        user_budget_ttl_seconds = max(
            60, _int_env("REMEDIATION_USER_BUDGET_TTL_SECONDS", 2 * 3600)
        )
        user_day_budget_ttl_seconds = max(
            60, _int_env("REMEDIATION_USER_DAY_BUDGET_TTL_SECONDS", 2 * 24 * 3600)
        )

        outbox_pending_threshold = max(
            0, _int_env("REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD", 5000)
        )
        fuse_max_targets = max(0, _int_env("REMEDIATION_FUSE_MAX_TARGETS", 3))
        outbox_pending = await _count_outbox_pending()
        fuse_triggered = outbox_pending_threshold > 0 and outbox_pending >= outbox_pending_threshold

        now = datetime.now(timezone.utc)
        crawl_run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_posts:{task.id}"))
        preferred_days = int(getattr(topic_profile, "preferred_days", 0) or 0) if topic_profile is not None else 0
        backfill_days = 30
        backfill_slice_days = 7
        if preferred_days > 30:
            # 对窄题：适当放宽窗口，但限制切片数量，避免一次性下太多 target 压垮队列。
            backfill_days = max(30, min(preferred_days, 180))
            backfill_slice_days = 30 if backfill_days > 90 else 7
        # Budget teeth (Phase106-3): cap targets per task/user + global fuse.
        try:
            from app.services.crawl.time_slicer import generate_slices

            since_dt = now - timedelta(days=max(1, int(backfill_days)))
            until_dt = now
            slices = generate_slices(
                since_dt,
                until_dt,
                slice_days=max(1, int(backfill_slice_days)),
                overlap_seconds=0,
            )
            slices_count = len(slices)
        except Exception:
            slices_count = 0

        total_posts_budget = 300
        if slices_count <= 0 or total_posts_budget <= 0:
            requested_targets_estimate = len(sorted(set(communities)))
        else:
            base = total_posts_budget // slices_count
            remainder = total_posts_budget % slices_count
            positive_slices = slices_count if base > 0 else remainder
            requested_targets_estimate = len(sorted(set(communities))) * int(positive_slices)
        max_targets_allowed = requested_targets_estimate
        budget_detail: dict[str, Any] = {
            "enabled": bool(budget_enabled),
            "requested_targets_estimate": int(requested_targets_estimate),
        }

        outbox_enqueued = 0
        outbox_deduped = 0

        if fuse_triggered:
            max_targets_allowed = min(max_targets_allowed, fuse_max_targets)
            budget_detail["circuit_breaker"] = {
                "triggered": True,
                "outbox_pending": int(outbox_pending),
                "threshold": int(outbox_pending_threshold),
                "max_targets": int(fuse_max_targets),
            }
        else:
            budget_detail["circuit_breaker"] = {
                "triggered": False,
                "outbox_pending": int(outbox_pending),
                "threshold": int(outbox_pending_threshold),
            }

        # Best-effort stateful budgets via Redis (disable-by-failure).
        if budget_enabled:
            try:
                settings = get_settings()
                budget_redis = _get_remediation_budget_redis(settings)
                task_budget_key = f"budget:remediation:task:{task.id}"
                current_task_targets = int((await budget_redis.get(task_budget_key)) or 0)
                remaining_task = max(0, per_task_budget - current_task_targets)
                budget_detail["task_budget"] = {
                    "key": task_budget_key,
                    "max": int(per_task_budget),
                    "used": int(current_task_targets),
                    "remaining": int(remaining_task),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_task)

                user_id = getattr(task, "user_id", None)
                if user_id is not None:
                    level = _membership_level()
                    hourly_budget = max(0, _hourly_user_budget(level))
                    bucket = _hour_bucket(now)
                    user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                    current_user_targets = int((await budget_redis.get(user_budget_key)) or 0)
                    remaining_user = max(0, hourly_budget - current_user_targets)
                    budget_detail["user_budget_hour"] = {
                        "key": user_budget_key,
                        "level": level,
                        "max": int(hourly_budget),
                        "used": int(current_user_targets),
                        "remaining": int(remaining_user),
                    }
                    max_targets_allowed = min(max_targets_allowed, remaining_user)

                    daily_budget = max(0, _daily_user_budget(level))
                    day_bucket = _day_bucket(now)
                    user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                    current_day_targets = int((await budget_redis.get(user_day_key)) or 0)
                    remaining_day = max(0, daily_budget - current_day_targets)
                    budget_detail["user_budget_day"] = {
                        "key": user_day_key,
                        "level": level,
                        "max": int(daily_budget),
                        "used": int(current_day_targets),
                        "remaining": int(remaining_day),
                    }
                    max_targets_allowed = min(max_targets_allowed, remaining_day)
            except Exception as exc:
                budget_detail["budget_store_error"] = str(exc)

        max_targets_allowed = max(0, int(max_targets_allowed))
        budget_detail["max_targets_allowed"] = int(max_targets_allowed)

        if max_targets_allowed <= 0:
            return [
                {
                    "type": "backfill_posts",
                    "queue": BACKFILL_POSTS_QUEUE,
                    "crawl_run_id": crawl_run_id,
                    "targets": 0,
                    "outbox_enqueued": 0,
                    "outbox_deduped": 0,
                    "budget_detail": budget_detail,
                    "blocked_reason": "budget_or_fuse_blocked",
                }
            ]

        async with SessionFactory() as session:
            target_ids = await plan_auto_backfill_posts_targets(
                session=session,
                crawl_run_id=crawl_run_id,
                communities=communities,
                now=now,
                days=backfill_days,
                slice_days=backfill_slice_days,
                total_posts_budget=300,
                reason="analysis_preflight_insufficient_samples",
                max_targets=max_targets_allowed,
            )
            if not target_ids:
                return [
                    {
                        "type": "backfill_posts",
                        "queue": BACKFILL_POSTS_QUEUE,
                        "crawl_run_id": crawl_run_id,
                        "targets": 0,
                        "outbox_enqueued": 0,
                        "outbox_deduped": 0,
                        "budget_detail": budget_detail,
                        "blocked_reason": "budget_or_fuse_blocked"
                        if max_targets_allowed <= 0
                        else "planner_returned_empty",
                    }
                ]
            for target_id in target_ids:
                inserted = await enqueue_execute_target_outbox(
                    session,
                    target_id=target_id,
                    queue=BACKFILL_POSTS_QUEUE,
                )
                if inserted:
                    outbox_enqueued += 1
                else:
                    outbox_deduped += 1
            await session.commit()

        # Persist consumed budget (best-effort).
        if budget_enabled and outbox_enqueued > 0:
            try:
                settings = get_settings()
                budget_redis = _get_remediation_budget_redis(settings)
                task_budget_key = f"budget:remediation:task:{task.id}"
                await budget_redis.incrby(task_budget_key, int(outbox_enqueued))
                await budget_redis.expire(task_budget_key, int(budget_task_ttl_seconds))
                user_id = getattr(task, "user_id", None)
                if user_id is not None:
                    bucket = _hour_bucket(now)
                    user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                    await budget_redis.incrby(user_budget_key, int(outbox_enqueued))
                    await budget_redis.expire(user_budget_key, int(user_budget_ttl_seconds))
                    day_bucket = _day_bucket(now)
                    user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                    await budget_redis.incrby(user_day_key, int(outbox_enqueued))
                    await budget_redis.expire(user_day_key, int(user_day_budget_ttl_seconds))
            except Exception:
                pass

        trimmed_ids, total_ids, truncated = _truncate_target_ids(list(target_ids or []))
        return [
            {
                "type": "backfill_posts",
                "queue": BACKFILL_POSTS_QUEUE,
                "crawl_run_id": crawl_run_id,
                "targets": len(target_ids),
                "outbox_enqueued": int(outbox_enqueued),
                "outbox_deduped": int(outbox_deduped),
                "budget_detail": budget_detail,
                "target_ids": trimmed_ids,
                "target_ids_total": int(total_ids),
                "target_ids_truncated": bool(truncated),
                "communities": sorted(set(communities)),
                "window_days": backfill_days,
                "slice_days": backfill_slice_days,
            }
        ]
    except Exception as exc:  # pragma: no cover - best effort only
        logger.warning("Auto backfill scheduling skipped: %s", exc, exc_info=True)
        return []


async def _schedule_auto_backfill_for_missing_comments(
    *,
    task: TaskSummary,
    topic_profile: "TopicProfile | None",
    posts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """
    Contract B（闭环补量）：当分析样本里的帖子“看起来有评论”，但库里评论为 0/很少时，
    系统自动下单 backfill_comments targets，并把动作写进 sources.remediation_actions。
    """
    settings = get_settings()
    if not bool(getattr(settings, "incremental_comments_backfill_enabled", True)):
        return []

    raw_posts = list(posts or [])
    if not raw_posts:
        return []

    allowed: set[str] = set()
    if topic_profile is not None and getattr(topic_profile, "allowed_communities", None):
        try:
            allowed = {
                normalize_subreddit(str(x or ""))
                for x in (topic_profile.allowed_communities or [])
                if str(x or "").strip()
            }
        except Exception:
            allowed = set()

    def _post_id(post: Mapping[str, Any]) -> str:
        return str(post.get("id") or "").strip()

    def _subreddit(post: Mapping[str, Any]) -> str:
        return normalize_subreddit(str(post.get("subreddit") or ""))

    def _num_comments(post: Mapping[str, Any]) -> int:
        raw = post.get("num_comments", 0)
        try:
            return max(0, int(raw or 0))
        except (TypeError, ValueError):
            return 0

    # Candidates: top scored posts with expected comments > 0
    candidates: list[dict[str, Any]] = []
    for post in raw_posts:
        pid = _post_id(post)
        if not pid:
            continue
        if not _looks_like_reddit_post_id(pid):
            continue
        sub = _subreddit(post)
        if allowed and sub not in allowed:
            continue
        # NOTE（大白话）：
        # 有些数据源/缓存并不会把 num_comments 填准（常见是 0）。
        # 但我们在“评论为 0 → 窄题永远不自愈”的场景里，仍需要敢于下一个很小的补量单来验证。
        # 所以：num_comments=0 时，只要帖子有一定热度（score>0），也允许进入候选。
        num_comments = _num_comments(post)
        score = int(post.get("score") or 0)
        if num_comments <= 0 and score <= 0:
            continue
        candidates.append(
            {
                "id": pid,
                "subreddit": sub or "unknown",
                "num_comments": num_comments,
                "score": score,
            }
        )
    if not candidates:
        return []

    candidates.sort(key=lambda p: (int(p.get("score") or 0), int(p.get("num_comments") or 0)), reverse=True)
    candidate_ids = [str(p["id"]) for p in candidates][:50]

    # Load existing comment counts per post_id
    existing_counts: dict[str, int] = {}
    try:
        async with SessionFactory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT source_post_id, count(*) AS cnt
                    FROM comments
                    WHERE source = 'reddit'
                      AND source_post_id = ANY(:ids)
                    GROUP BY source_post_id
                    """
                ),
                {"ids": candidate_ids},
            )
            for row in rows.mappings().all():
                pid = str(row.get("source_post_id") or "").strip()
                if not pid:
                    continue
                try:
                    existing_counts[pid] = int(row.get("cnt") or 0)
                except (TypeError, ValueError):
                    existing_counts[pid] = 0
    except Exception:  # pragma: no cover - best effort only
        existing_counts = {}

    missing: list[dict[str, Any]] = []
    for item in candidates:
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        if existing_counts.get(pid, 0) <= 0:
            missing.append(item)

    if not missing:
        return []

    max_posts = int(getattr(settings, "incremental_comments_backfill_max_posts", 5) or 0)
    max_posts = max(1, min(max_posts, 10))
    missing = missing[:max_posts]

    comments_limit = int(getattr(settings, "incremental_comments_backfill_limit", 50) or 50)
    comments_limit = max(1, min(comments_limit, 200))
    depth = int(getattr(settings, "incremental_comments_backfill_depth", 2) or 2)
    depth = max(1, min(depth, 8))
    mode = str(getattr(settings, "incremental_comments_backfill_mode", "smart_shallow") or "smart_shallow").strip()
    if not mode:
        mode = "smart_shallow"
    queue = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")

    import uuid
    from app.services.crawl.plan_contract import (
        CrawlPlanContract,
        CrawlPlanLimits,
        compute_idempotency_key,
        compute_idempotency_key_human,
    )
    from app.services.crawler_runs_service import ensure_crawler_run
    from app.services.crawler_run_targets_service import ensure_crawler_run_target
    from app.services.task_outbox_service import enqueue_execute_target_outbox

    crawl_run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_comments:{task.id}"))
    now = datetime.now(timezone.utc)

    def _truthy_env(name: str, default: str) -> bool:
        raw = os.getenv(name, default).strip().lower()
        return raw in {"1", "true", "yes", "y", "on"}

    def _int_env(name: str, default: int) -> int:
        raw = os.getenv(name, str(default)).strip()
        try:
            return int(raw)
        except (TypeError, ValueError):
            return int(default)

    async def _count_outbox_pending() -> int:
        try:
            async with SessionFactory() as session_outbox:
                res = await session_outbox.execute(
                    text("SELECT COUNT(*) FROM task_outbox WHERE status = 'pending'")
                )
                return int(res.scalar() or 0)
        except Exception:
            return 0

    def _hour_bucket(dt: datetime) -> str:
        safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return safe.astimezone(timezone.utc).strftime("%Y%m%d%H")

    def _day_bucket(dt: datetime) -> str:
        safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return safe.astimezone(timezone.utc).strftime("%Y%m%d")

    def _membership_level() -> str:
        raw = str(getattr(task, "membership_level", None) or "free").strip().lower()
        return raw if raw in {"free", "pro", "enterprise"} else "free"

    def _hourly_user_budget(level: str) -> int:
        if level == "enterprise":
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_ENTERPRISE", 1000)
        if level == "pro":
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_PRO", 200)
        return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_FREE", 50)

    def _daily_user_budget(level: str) -> int:
        if level == "enterprise":
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_ENTERPRISE", 5000)
        if level == "pro":
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_PRO", 1000)
        return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_FREE", 200)

    budget_enabled = _truthy_env("REMEDIATION_BUDGET_ENABLED", "1")
    per_task_budget = max(1, _int_env("REMEDIATION_TASK_TARGET_BUDGET", 200))
    budget_task_ttl_seconds = max(
        60, _int_env("REMEDIATION_TASK_BUDGET_TTL_SECONDS", 24 * 3600)
    )
    user_budget_ttl_seconds = max(
        60, _int_env("REMEDIATION_USER_BUDGET_TTL_SECONDS", 2 * 3600)
    )
    user_day_budget_ttl_seconds = max(
        60, _int_env("REMEDIATION_USER_DAY_BUDGET_TTL_SECONDS", 2 * 24 * 3600)
    )

    outbox_pending_threshold = max(
        0, _int_env("REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD", 5000)
    )
    fuse_max_targets = max(0, _int_env("REMEDIATION_FUSE_MAX_TARGETS", 3))
    outbox_pending = await _count_outbox_pending()
    fuse_triggered = (
        outbox_pending_threshold > 0 and outbox_pending >= outbox_pending_threshold
    )

    requested_targets = len(missing)
    max_targets_allowed = requested_targets
    budget_detail: dict[str, Any] = {
        "enabled": bool(budget_enabled),
        "requested_targets": int(requested_targets),
        "circuit_breaker": {
            "triggered": bool(fuse_triggered),
            "outbox_pending": int(outbox_pending),
            "threshold": int(outbox_pending_threshold),
            "max_targets": int(fuse_max_targets),
        },
    }
    if fuse_triggered:
        max_targets_allowed = min(max_targets_allowed, fuse_max_targets)

    if budget_enabled:
        try:
            budget_redis = _get_remediation_budget_redis(settings)
            task_budget_key = f"budget:remediation:task:{task.id}"
            current_task_targets = int((await budget_redis.get(task_budget_key)) or 0)
            remaining_task = max(0, per_task_budget - current_task_targets)
            budget_detail["task_budget"] = {
                "key": task_budget_key,
                "max": int(per_task_budget),
                "used": int(current_task_targets),
                "remaining": int(remaining_task),
            }
            max_targets_allowed = min(max_targets_allowed, remaining_task)

            user_id = getattr(task, "user_id", None)
            if user_id is not None:
                level = _membership_level()
                hourly_budget = max(0, _hourly_user_budget(level))
                bucket = _hour_bucket(now)
                user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                current_user_targets = int((await budget_redis.get(user_budget_key)) or 0)
                remaining_user = max(0, hourly_budget - current_user_targets)
                budget_detail["user_budget_hour"] = {
                    "key": user_budget_key,
                    "level": level,
                    "max": int(hourly_budget),
                    "used": int(current_user_targets),
                    "remaining": int(remaining_user),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_user)

                daily_budget = max(0, _daily_user_budget(level))
                day_bucket = _day_bucket(now)
                user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                current_day_targets = int((await budget_redis.get(user_day_key)) or 0)
                remaining_day = max(0, daily_budget - current_day_targets)
                budget_detail["user_budget_day"] = {
                    "key": user_day_key,
                    "level": level,
                    "max": int(daily_budget),
                    "used": int(current_day_targets),
                    "remaining": int(remaining_day),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_day)
        except Exception as exc:
            budget_detail["budget_store_error"] = str(exc)

    max_targets_allowed = max(0, int(max_targets_allowed))
    budget_detail["max_targets_allowed"] = int(max_targets_allowed)

    if max_targets_allowed <= 0:
        return [
            {
                "type": "backfill_comments",
                "queue": queue,
                "crawl_run_id": crawl_run_id,
                "targets": 0,
                "outbox_enqueued": 0,
                "outbox_deduped": 0,
                "budget_detail": budget_detail,
                "blocked_reason": "budget_or_fuse_blocked",
                "posts": [str(x.get("id") or "") for x in missing if x.get("id")][:10],
            }
        ]

    missing = missing[:max_targets_allowed]

    target_ids: list[str] = []
    outbox_enqueued = 0
    outbox_deduped = 0
    try:
        async with SessionFactory() as session:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={
                    "mode": "analysis_preflight_comments",
                    "task_id": str(task.id),
                    "topic_profile_id": getattr(task, "topic_profile_id", None),
                    "created_at": now.isoformat(),
                },
            )

            for item in missing:
                pid = str(item.get("id") or "").strip()
                sub = normalize_subreddit(str(item.get("subreddit") or "")) or "unknown"
                plan = CrawlPlanContract(
                    plan_kind="backfill_comments",
                    target_type="post_ids",
                    target_value=pid,
                    reason="analysis_preflight_missing_comments",
                    limits=CrawlPlanLimits(comments_limit=comments_limit),
                    meta={
                        "subreddit": sub,
                        "mode": mode,
                        "depth": depth,
                        "sort": "confidence",
                        "smart_top_limit": 30,
                        "smart_new_limit": 20,
                        "smart_reply_top_limit": 15,
                        "smart_reply_per_top": 1,
                        "smart_total_limit": comments_limit,
                        "smart_top_sort": "top",
                        "smart_new_sort": "new",
                    },
                )
                idempotency_key = compute_idempotency_key(plan)
                idempotency_key_human = compute_idempotency_key_human(plan)
                target_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                    )
                )
                await ensure_crawler_run_target(
                    session,
                    community_run_id=target_id,
                    crawl_run_id=crawl_run_id,
                    subreddit=sub,
                    status="queued",
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    config=plan.model_dump(mode="json"),
                )
                inserted = await enqueue_execute_target_outbox(
                    session,
                    target_id=target_id,
                    queue=queue,
                )
                if inserted:
                    outbox_enqueued += 1
                else:
                    outbox_deduped += 1
                target_ids.append(target_id)

            await session.commit()
    except Exception as exc:  # pragma: no cover - best effort only
        logger.warning("Auto comment backfill scheduling skipped: %s", exc, exc_info=True)
        return []

    if budget_enabled and outbox_enqueued > 0:
        try:
            budget_redis = _get_remediation_budget_redis(settings)
            task_budget_key = f"budget:remediation:task:{task.id}"
            await budget_redis.incrby(task_budget_key, int(outbox_enqueued))
            await budget_redis.expire(task_budget_key, int(budget_task_ttl_seconds))
            user_id = getattr(task, "user_id", None)
            if user_id is not None:
                bucket = _hour_bucket(now)
                user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                await budget_redis.incrby(user_budget_key, int(outbox_enqueued))
                await budget_redis.expire(user_budget_key, int(user_budget_ttl_seconds))
                day_bucket = _day_bucket(now)
                user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                await budget_redis.incrby(user_day_key, int(outbox_enqueued))
                await budget_redis.expire(user_day_key, int(user_day_budget_ttl_seconds))
        except Exception:
            pass

    return [
        {
            "type": "backfill_comments",
            "queue": queue,
            "crawl_run_id": crawl_run_id,
            "targets": len(target_ids),
            "outbox_enqueued": int(outbox_enqueued),
            "outbox_deduped": int(outbox_deduped),
            "budget_detail": budget_detail,
            "target_ids": _truncate_target_ids(list(target_ids))[0],
            "target_ids_total": int(len(target_ids)),
            "target_ids_truncated": bool(len(target_ids) > DATA_LINEAGE_TARGET_IDS_MAX),
            "mode": mode,
            "comments_limit": comments_limit,
            "depth": depth,
            "posts": [str(x.get("id") or "") for x in missing if x.get("id")],
        }
    ]

# Baseline community catalogue; in production这将由缓存/数据库提供
# 扩展社区池以支持更多领域（加密货币、股票投资、金融等）
COMMUNITY_CATALOGUE: List[CommunityProfile] = [
    # 创业和商业
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
    # 加密货币相关社区
    CommunityProfile(
        name="r/CryptoCurrency",
        categories=("crypto", "blockchain", "trading"),
        description_keywords=(
            "crypto",
            "bitcoin",
            "ethereum",
            "blockchain",
            "trading",
            "defi",
        ),
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
    # 股票投资相关社区
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
        description_keywords=(
            "investing",
            "portfolio",
            "dividend",
            "etf",
            "retirement",
        ),
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
    # 金融和个人理财
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
        description_keywords=(
            "fire",
            "retirement",
            "investing",
            "savings",
            "passive income",
        ),
        daily_posts=180,
        avg_comment_length=95,
        cache_hit_rate=0.81,
    ),
]


def _tokenise(text: str) -> List[str]:
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


def _build_reddit_search_queries(*, tokens: Sequence[str], lookback_days: int) -> list[str]:
    """
    Build compact Reddit search queries from keyword tokens.

    Human intent (Phase105/106, plain language):
    - Reddit search is our "narrow topic booster": we want queries that include the anchor (e.g. Shopify)
      and some context (e.g. ROAS/ads), without polluting the query with non-English tokens.
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

    # Use 2 compact combinations, similar to the existing strategy.
    query1 = " ".join(cleaned[:3]).strip()
    query2 = (
        " ".join(cleaned[1:4]).strip()
        if len(cleaned) > 3
        else " ".join(cleaned[:2]).strip()
    )
    queries = [q for q in (query1, query2) if q]

    # When scanning longer windows, add a slightly broader query (anchor + 1 context) if possible.
    if lookback_days >= 365 and len(cleaned) >= 2:
        queries.append(" ".join(cleaned[:2]).strip())

    # Dedupe, keep order.
    out: list[str] = []
    seen_q: set[str] = set()
    for q in queries:
        key = q.lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        out.append(q)
    return out


def _extract_keywords(description: str, max_keywords: int = 12) -> List[str]:
    tokens = [token for token in _tokenise(description) if len(token) >= 3]
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(max_keywords)]


def _augment_keywords(base: Sequence[str], description: str) -> List[str]:
    """Augment keywords with common英中领域同义词，提升匹配度（尤其中文输入）。

    设计目标：快速、可控；当过滤后样本过少时会自动回退。
    """
    kws: set[str] = set(w.lower() for w in base)
    # 常见概念同义词（面向本项目域）
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
    }
    # 中文触发词 → 英文关键字
    zh_triggers = {
        "笔记": ["note", "notes"],
        "总结": ["summary", "summarize"],
        "创业": ["startup", "entrepreneur"],
        "市场": ["market", "insight"],
        "洞察": ["insight"],
        "产品": ["product"],
        "AI": ["ai"],
    }
    desc_lower = description.lower()
    for root, variants in canon.items():
        if root in desc_lower or any(v in kws for v in variants):
            kws.update(variants)
    for zh, variants in zh_triggers.items():
        if zh in description:
            kws.update(variants)
    return list(kws)


def _filter_posts_by_keywords(
    posts: Sequence[Dict[str, Any]], keywords: Sequence[str]
) -> List[Dict[str, Any]]:
    if not posts or not keywords:
        return list(posts)
    keys = [k.lower() for k in keywords if k]
    filtered: List[Dict[str, Any]] = []
    for p in posts:
        title = str(p.get("title", "")).lower()
        summary = str(p.get("summary", "")).lower()
        text = f"{title} {summary}"
        if any(k in text for k in keys):
            filtered.append(p)
    # 避免过度过滤：若过滤后小于原来20%，则回退使用原集合
    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def _apply_keyword_stopwords(
    keywords: Sequence[str],
    blacklist_config: Any | None = None,
) -> List[str]:
    if not keywords:
        return []

    stopwords: set[str] = set()
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
    if not stopwords:
        stopwords = set(_DEFAULT_EXPANSION_STOPWORDS)

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


def _filter_posts_by_blocklist(
    posts: Sequence[Dict[str, Any]],
    blocklist: Sequence[str],
) -> List[Dict[str, Any]]:
    if not posts or not blocklist:
        return list(posts)
    keys = [k.lower() for k in blocklist if k]
    if not keys:
        return list(posts)

    filtered: List[Dict[str, Any]] = []
    for p in posts:
        title = str(p.get("title", "")).lower()
        summary = str(p.get("summary", "")).lower()
        body = str(p.get("body", "")).lower()
        text = f"{title} {summary} {body}"
        if any(k in text for k in keys):
            continue
        filtered.append(p)

    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def _filter_posts_by_blacklist_config(
    posts: Sequence[Dict[str, Any]],
    blacklist_config: Any | None,
) -> List[Dict[str, Any]]:
    if not posts or blacklist_config is None:
        return list(posts)

    filtered: List[Dict[str, Any]] = []
    for p in posts:
        title = str(p.get("title", "") or "")
        summary = str(p.get("summary", "") or "")
        body = str(p.get("body", "") or "")
        text = f"{title} {summary} {body}".strip()
        author = str(p.get("author") or p.get("author_name") or "").strip()
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
        filtered.append(p)

    return filtered if len(filtered) >= max(1, int(len(posts) * 0.2)) else list(posts)


def _apply_topic_profile_context_filter(
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
    # require_context_for_fetch 是“窄题双钥匙”的硬门槛：宁可变少/变空，也不要回退放宽导致跑偏。
    return filtered


def _apply_topic_profile_required_filter(
    posts: Sequence[Dict[str, Any]],
    profile: TopicProfile,
) -> List[Dict[str, Any]]:
    """
    双钥匙的第一把钥匙：锚点词（required_entities_any）必须命中。

    NOTE（大白话）：
    - 例如 Shopify Ads 这种窄题：没有提到 Shopify，本质就不是我们要的盘。
    - 这里不做“<20% 回退”，因为回退等于放弃锚点约束，会直接把赛道带歪。
    """
    if not posts:
        return []
    required = [str(t).strip().lower() for t in (profile.required_entities_any or []) if str(t).strip()]
    if not required:
        return list(posts)

    kept: list[Dict[str, Any]] = []
    for p in posts:
        # 现实世界：在 r/<brand> 这种“品牌社区”里，很多帖子默认语境就是该品牌，
        # 标题/正文未必会重复写品牌名；如果仍强制要求文本命中，会把主战场误判成“0 样本”。
        # 规则：当 subreddit 本身就包含 required 锚点词（如 r/shopify），视为已满足第一把钥匙。
        raw_subreddit = str(p.get("subreddit") or "").strip()
        subreddit = normalize_subreddit(raw_subreddit)
        if subreddit:
            slug = subreddit.removeprefix("r/").strip().lower()
            if slug:
                for term in required:
                    if not term or " " in term or len(term) < 3:
                        continue
                    if term in slug:
                        kept.append(p)
                        break
                else:
                    # not matched by subreddit; fall back to text anchor check below
                    pass
                if kept and kept[-1] is p:
                    continue

        title = str(p.get("title", "")).lower()
        summary = str(p.get("summary", "")).lower()
        body = str(p.get("body", "")).lower()
        text = str(p.get("text", "")).lower()
        selftext = str(p.get("selftext", "")).lower()
        hay = f"{title} {summary} {body} {text} {selftext}"
        if any(term in hay for term in required):
            kept.append(p)
    return kept


async def _attach_post_scores(
    session: "AsyncSession",
    posts: Sequence[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], dict[str, Any]]:
    if not posts:
        return list(posts), {
            "scored_posts": 0,
            "score_coverage": 0.0,
            "pool_counts": {},
            "noise_posts": 0,
        }

    source_ids: list[str] = []
    for post in posts:
        raw = str(post.get("id") or "").strip()
        if raw:
            source_ids.append(raw)

    if not source_ids:
        return list(posts), {
            "scored_posts": 0,
            "score_coverage": 0.0,
            "pool_counts": {},
            "noise_posts": 0,
        }

    unique_ids = list(dict.fromkeys(source_ids))
    rows: list[dict[str, Any]] = []

    async def _fetch_scores(table_name: str, where_suffix: str = "") -> list[dict[str, Any]]:
        result = await session.execute(
            text(
                f"""
                SELECT
                    pr.source_post_id AS source_post_id,
                    ps.business_pool,
                    ps.value_score,
                    ps.opportunity_score,
                    ps.sentiment,
                    ps.purchase_intent_score
                FROM posts_raw pr
                JOIN {table_name} ps ON ps.post_id = pr.id
                WHERE pr.source_post_id = ANY(:source_ids)
                {where_suffix}
                """
            ),
            {"source_ids": unique_ids},
        )
        return [dict(row) for row in result.mappings().all()]

    try:
        rows = await _fetch_scores("post_scores_latest_v")
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("post_scores_latest_v unavailable, fallback to post_scores: %s", exc)

    if not rows:
        try:
            rows = await _fetch_scores("post_scores", "AND ps.is_latest = true")
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Failed to attach post scores: %s", exc)
            return list(posts), {
                "scored_posts": 0,
                "score_coverage": 0.0,
                "pool_counts": {},
                "noise_posts": 0,
            }

    score_map = {str(row.get("source_post_id")): row for row in rows}
    pool_counts: Counter[str] = Counter()
    scored_posts = 0
    enriched: List[Dict[str, Any]] = []

    for post in posts:
        payload = dict(post)
        source_id = str(post.get("id") or "").strip()
        row = score_map.get(source_id)
        if row:
            scored_posts += 1
            pool = str(row.get("business_pool") or "").strip() or "unknown"
            pool_counts[pool] += 1
            for field in (
                "business_pool",
                "value_score",
                "opportunity_score",
                "sentiment",
                "purchase_intent_score",
            ):
                if row.get(field) is not None:
                    payload[field] = row.get(field)
        enriched.append(payload)

    noise_posts = pool_counts.get("noise", 0)
    score_coverage = scored_posts / len(posts) if posts else 0.0
    stats = {
        "scored_posts": scored_posts,
        "score_coverage": round(score_coverage, 2),
        "pool_counts": dict(pool_counts),
        "noise_posts": noise_posts,
    }
    return enriched, stats


def _apply_post_score_policy(
    posts: Sequence[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], dict[str, Any]]:
    if not posts:
        return [], {"noise_posts": 0, "noise_by_community": {}}

    noise_by_community: Counter[str] = Counter()
    filtered: List[Dict[str, Any]] = []

    for post in posts:
        pool_raw = str(post.get("business_pool") or "").strip().lower()
        if pool_raw == "noise":
            community = str(post.get("subreddit") or "unknown").strip() or "unknown"
            noise_by_community[community] += 1
            continue

        pool = pool_raw or "unknown"
        weight = BUSINESS_POOL_WEIGHTS.get(pool, BUSINESS_POOL_WEIGHTS["unknown"])
        base_score = float(post.get("score", 0) or 0)
        value_score = float(post.get("value_score", 0) or 0)
        priority_score = base_score * weight + value_score * VALUE_SCORE_WEIGHT

        payload = dict(post)
        payload["priority_score"] = round(priority_score, 2)
        payload["pool_weight"] = round(weight, 2)
        filtered.append(payload)

    stats = {
        "noise_posts": sum(noise_by_community.values()),
        "noise_by_community": dict(noise_by_community),
    }
    return filtered, stats


def _score_community(keywords: Sequence[str], profile: CommunityProfile) -> float:
    if not keywords:
        keyword_score = 0.0
    else:
        overlap = len(set(keywords) & set(profile.description_keywords))
        keyword_score = overlap / len(keywords)

    activity_score = min(profile.daily_posts / 200, 1.0)
    quality_score = min(profile.avg_comment_length / 120, 1.0)
    return keyword_score * 0.4 + activity_score * 0.3 + quality_score * 0.3


def _classify_pain_severity(frequency: int, sentiment_score: float) -> str:
    """Classify pain point severity using frequency and sentiment heuristics."""
    if frequency >= 5 or sentiment_score <= -0.6:
        return "high"
    if frequency >= 3 or sentiment_score <= -0.3:
        return "medium"
    return "low"


def _normalise_cache_hit_rate(hit_rate: float) -> float:
    """Ensure cache hit rate honours the 90% cache-first commitment."""
    return min(max(hit_rate, CACHE_HIT_RATE_TARGET), 1.0)


def _build_collection_warnings(
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


async def _check_trend_views_freshness() -> tuple[bool, list[str]]:
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


async def _fetch_coverage_summary(
    community_names: Sequence[str],
) -> dict[str, Any]:
    names = sorted(
        {
            _normalise_community_name(name)
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
                CommunityCache.community_name,
                CommunityCache.backfill_status,
                CommunityCache.coverage_months,
                CommunityCache.sample_posts,
                CommunityCache.sample_comments,
                CommunityCache.backfill_capped,
            ).where(CommunityCache.community_name.in_(names))
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
        status = str(row.get("backfill_status") or "unknown").strip() or "unknown"
        status_counts[status] += 1
        coverage = row.get("coverage_months")
        if isinstance(coverage, int):
            coverage_values.append(coverage)
        capped = bool(row.get("backfill_capped") or False)
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


def _format_collection_warning_lines(sources: Mapping[str, Any]) -> list[str]:
    warnings = sources.get("collection_warnings") or []
    if not isinstance(warnings, list):
        return []
    lines: list[str] = []
    stale_cache = sources.get("stale_cache_subreddits") or []
    stale_fallback = sources.get("stale_cache_fallback_subreddits") or []
    if "stale_cache_detected" in warnings:
        lines.append(f"- 发现 {len(stale_cache)} 个社区缓存过期，时效性下降。")
    if "stale_cache_fallback" in warnings:
        lines.append(f"- 有 {len(stale_fallback)} 个社区使用旧缓存兜底（API/限流失败）。")
    if "reddit_rate_limited" in warnings:
        lines.append("- Reddit API 触发限流，部分社区未能实时拉取。")
    if "reddit_api_error" in warnings:
        lines.append("- Reddit API 请求失败，部分社区未能实时拉取。")
    return lines


def _community_pool_priority_order(model: type[CommunityPool]) -> Any:
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


def _select_top_communities(keywords: Sequence[str]) -> List[CommunityProfile]:
    scored = [
        (profile, _score_community(keywords, profile))
        for profile in COMMUNITY_CATALOGUE
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    initial = [item[0] for item in scored[:20]]  # preselect

    if not initial:
        return []

    avg_hit = sum(_normalise_cache_hit_rate(p.cache_hit_rate) for p in initial) / len(
        initial
    )
    target_count = _determine_target_count(avg_hit)
    selected: List[CommunityProfile] = []
    category_counts: Counter[str] = Counter()

    for profile in initial:
        if len(selected) >= target_count:
            break
        # 多样性：同一类别最多5个
        if any(category_counts[cat] >= 5 for cat in profile.categories):
            continue
        selected.append(profile)
        for cat in profile.categories:
            category_counts[cat] += 1

    return selected


def _filter_communities_by_mode(
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
        return [
            c
            for c in communities
            if _normalise_community_name(c.name) in ops
        ]

    return [
        c
        for c in communities
        if _normalise_community_name(c.name) not in ops
    ]


def _collect_data(
    communities: Sequence[CommunityProfile], keywords: Sequence[str]
) -> List[CollectedCommunity]:
    collected: List[CollectedCommunity] = []
    for profile in communities:
        posts = generate_demo_posts(profile, keywords)
        total_posts = len(posts)
        effective_hit_rate = _normalise_cache_hit_rate(profile.cache_hit_rate)
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


def _backfill_cache_misses(
    entries: Sequence[CollectedCommunity],
    keywords: Sequence[str],
) -> List[CollectedCommunity]:
    """Supplement missing cache data with deterministic synthetic posts."""
    if not entries:
        return []

    supplemented: List[CollectedCommunity] = []
    for entry in entries:
        if entry.posts:
            supplemented.append(entry)
            continue
        synthetic_entry = _collect_data([entry.profile], keywords)[0]
        supplemented.append(synthetic_entry)
    return supplemented


def _render_report(
    task_summary: TaskSummary,
    communities: Sequence[CollectedCommunity],
    insights: Dict[str, Any],
    sources: Dict[str, Any],
) -> str:
    """
    Build a Markdown report following the高价值样本结构：
    - 决策卡片
    - 市场概览
    - 战场推荐
    - 痛点与机会
    - 数据统计
    """
    community_names = [entry.profile.name for entry in communities]
    pain_counts = {}
    try:
        pain_counts = sources.get("pain_counts_by_community", {}) or {}
    except Exception:
        pain_counts = {}
    top_communities = sorted(
        communities,
        key=lambda c: (
            pain_counts.get(c.profile.name, 0),
            len(c.posts),
        ),
        reverse=True,
    )[:4]
    pain_points: list[Dict[str, Any]] = insights.get("pain_points", []) or []
    opportunities: list[Dict[str, Any]] = insights.get("opportunities", []) or []
    competitors: list[Dict[str, Any]] = insights.get("competitors", []) or []
    action_items: list[Dict[str, Any]] = insights.get("action_items", []) or []
    posts_analyzed = int(sources.get("posts_analyzed", 0) or 0)
    cache_hit_rate = float(sources.get("cache_hit_rate", 0.0) or 0.0)
    lookback_days = int(sources.get("lookback_days") or SAMPLE_LOOKBACK_DAYS)
    warning_lines = _format_collection_warning_lines(sources)
    warning_block = ""
    if warning_lines:
        warning_block = "\n## 数据提醒\n" + "\n".join(warning_lines)

    ps_ratio_value = sources.get("ps_ratio")
    ps_ratio = (
        f"{ps_ratio_value:.2f}"
        if isinstance(ps_ratio_value, (int, float))
        else f"{len(pain_points)}:{max(len(action_items), len(opportunities), 1)}"
    )

    def _format_list(items: list[str]) -> str:
        return "\n".join(f"- {it}" for it in items) if items else "- 暂无数据"

    def _fmt_pain(p: Dict[str, Any]) -> str:
        desc = str(p.get("description", "")).strip() or "未提取"
        freq = p.get("frequency") or p.get("mentions") or 1
        return f"- {desc}（频次 {freq}）"

    def _fmt_opp(o: Dict[str, Any]) -> str:
        desc = str(o.get("description", "")).strip() or "未提取"
        rel = o.get("relevance_score", 0)
        rel_str = f"{rel:.0%}" if isinstance(rel, (float, int)) else str(rel)
        audience = o.get("potential_users_est") or o.get("potential_users") or ""
        return f"- {desc}（相关度 {rel_str}，潜在用户 {audience}）"

    def _fmt_comp(c: Dict[str, Any]) -> str:
        name = c.get("name") or "未知"
        mentions = c.get("mentions", 0)
        sentiment = c.get("sentiment", "mixed")
        return f"- {name}：提及 {mentions} 次，情感 {sentiment}"

    top_pains = "\n".join(_fmt_pain(p) for p in pain_points[:3]) or "- 未识别到核心痛点"
    top_opps = "\n".join(_fmt_opp(o) for o in opportunities[:3]) or "- 未识别到机会"
    top_comps = "\n".join(_fmt_comp(c) for c in competitors[:5]) or "- 未识别到竞品/品牌"

    top_drivers_list = []
    for p in pain_points[:5]:
        driver = derive_driver_label(p.get("description", ""))
        item = f"- {driver} ← 来源痛点：{p.get('description','')}"
        if item not in top_drivers_list:
            top_drivers_list.append(item)
    top_drivers = "\n".join(top_drivers_list) or "- 暂无驱动力结论"

    # 用户之声
    quotes: list[str] = []
    for p in pain_points:
        for quote in p.get("user_examples", []) or []:
            if quote not in quotes:
                quotes.append(quote)
            if len(quotes) >= 5:
                break
        if len(quotes) >= 5:
            break
    quotes_block = "\n".join(f"- {q}" for q in quotes[:5]) or "- 暂无用户原声"

    # 机会卡详情
    def _format_opportunity_card(o: Dict[str, Any]) -> str:
        desc = str(o.get("description", "")).strip() or "未提取"
        users = o.get("potential_users") or o.get("potential_users_est") or "N/A"
        rel = o.get("relevance_score", 0)
        rel_str = f"{rel:.0%}" if isinstance(rel, (float, int)) else str(rel)
        linked = o.get("linked_pain_cluster") or "通用痛点"
        channels = o.get("top_channels") or []
        channel_str = ", ".join(channels) if channels else "多渠道"
        return (
            f"- {desc}\n"
            f"  - 目标社群：{', '.join(community_names[:3]) or '核心社区'}\n"
            f"  - 产品定位：解决 {linked}，强调 {rel_str} 相关度\n"
            f"  - 核心卖点：{', '.join(o.get('key_insights', [])[:3]) or '效率/稳定/合规'}\n"
            f"  - 潜在用户：{users}；渠道：{channel_str}"
        )

    opportunity_cards = "\n".join(
        _format_opportunity_card(o) for o in opportunities[:3]
    ) or "- 暂无机会卡"

    battlefield_blocks: list[str] = []
    for comm in top_communities:
        name = comm.profile.name
        description = ", ".join(comm.profile.categories) if comm.profile.categories else "相关社区"
        pains = ", ".join(
            [p.get("description", "") for p in pain_points[:2] if p.get("description")]
        ) or "关注用户运营/转化等常见问题"
        strategy = "提供可视化、自动化和本地化能力，验证 ROI"  # 通用策略语句
        battlefield_blocks.append(
            dedent(
                f"""
                - **{name}**
                  - 画像：{description}
                  - 常见痛点：{pains}
                  - 痛点热度：{pain_counts.get(name, 0)}
                  - 策略建议：{strategy}
                """
            ).strip()
        )

    battlefields = "\n".join(battlefield_blocks) or "- 暂无战场数据"

    report = dedent(
        f"""
        [Reddit Signal Scanner] 市场洞察报告

        ## 已分析赛道
        - 赛道：{task_summary.product_description.strip()}
        - 关键词：{", ".join(sources.get("keywords", []) or [])}
        - 数据范围：
          - 社区：{len(communities)} 个
          - 帖子：{posts_analyzed} 条（缓存命中率 {cache_hit_rate:.0%}）
          - 时间窗口：近 {lookback_days} 天，围绕上述关键词采样
        - 覆盖社区：{", ".join(community_names[:12])}

        ## 决策卡片
        1) 需求趋势：基于 {posts_analyzed} 条帖子，热度仍在（社区覆盖 {len(community_names)} 个）。
        2) 问题/解决方案比（P/S）：约 {ps_ratio}，痛点略高，需继续挖掘方案位。
        3) 核心战场：{", ".join(community_names[:4]) or "待补充"}。
        4) 明确机会点：{"; ".join([o.get("description","") for o in opportunities[:3]]) or "待补充"}。

        ## 概览
        - 竞争与品牌：\n{top_comps}
        - 痛点/解决方案比：{ps_ratio}（痛点 {len(pain_points)}，机会 {max(len(action_items), len(opportunities))}）

        ## 核心战场推荐
        {battlefields}

        ## 用户痛点（Top 3）
        {top_pains}

        ## Top 购买驱动力
        {top_drivers}

        ## 潜在机会（Top 3）
        {top_opps}

        ## 机会卡（结构化）
        {opportunity_cards}

        ## 用户之声（Quotes）
        {quotes_block}

        ## 数据与技术摘要
        - 帖子总数：{posts_analyzed}
        - 覆盖社区：{len(community_names)}
        - 新发现社区：{max(0, len(community_names) - len(set(community_names)))}（按名称去重估算）
        - 缓存命中率：{cache_hit_rate:.0%}
        {warning_block}
        """
    ).strip()

    return report


def _render_scouting_report(
    task_summary: TaskSummary,
    communities: Sequence[CollectedCommunity],
    sources: Dict[str, Any],
) -> str:
    community_names = [entry.profile.name for entry in communities]
    posts_analyzed = int(sources.get("posts_analyzed", 0) or 0)
    comments_analyzed = int(sources.get("comments_analyzed", 0) or 0)
    comments_status = str(sources.get("comments_pipeline_status") or "").strip() or "unknown"
    cache_hit_rate = float(sources.get("cache_hit_rate", 0.0) or 0.0)
    warning_lines = _format_collection_warning_lines(sources)
    warning_block = ""
    if warning_lines:
        warning_block = "\n## 数据提醒\n" + "\n".join(warning_lines)
    keywords = sources.get("keywords", []) or []

    ps_ratio_value = sources.get("ps_ratio")
    ps_ratio = (
        f"{ps_ratio_value:.2f}"
        if isinstance(ps_ratio_value, (int, float))
        else "N/A"
    )

    communities_detail = sources.get("communities_detail") or []
    top_communities: list[dict[str, Any]] = []
    if isinstance(communities_detail, list):
        try:
            candidates = [
                row
                for row in communities_detail
                if isinstance(row, dict) and row.get("name")
            ]
            candidates.sort(key=lambda x: int(x.get("mentions") or 0), reverse=True)
            top_communities = candidates[:4]
        except Exception:
            top_communities = []

    if not top_communities:
        top_communities = [{"name": name} for name in community_names[:4] if name]

    battlefield_lines = []
    for row in top_communities:
        name = str(row.get("name") or "").strip() or "unknown"
        categories = row.get("categories") or []
        label = ", ".join([str(x) for x in categories if x]) if isinstance(categories, list) else ""
        mentions = int(row.get("mentions") or 0) if isinstance(row.get("mentions"), (int, float)) else 0
        extra = []
        if label:
            extra.append(f"画像：{label}")
        if mentions:
            extra.append(f"提及：{mentions}")
        extra_text = f"（{'；'.join(extra)}）" if extra else ""
        battlefield_lines.append(f"- **{name}**{extra_text}")
    battlefields = "\n".join(battlefield_lines) or "- 暂无战场数据"

    remediation_actions = sources.get("remediation_actions") or []
    remediation_note = ""
    try:
        if isinstance(remediation_actions, list) and remediation_actions:
            backfill_posts = sum(
                int(a.get("targets") or 0)
                for a in remediation_actions
                if isinstance(a, dict) and a.get("type") == "backfill_posts"
            )
            backfill_comments = sum(
                int(a.get("targets") or 0)
                for a in remediation_actions
                if isinstance(a, dict) and a.get("type") == "backfill_comments"
            )
            parts: list[str] = []
            if backfill_posts:
                parts.append(f"帖子补抓下单 {backfill_posts} 个 target")
            if backfill_comments:
                parts.append(f"评论补抓下单 {backfill_comments} 个 target")
            if parts:
                remediation_note = "系统已自动补量：" + "，".join(parts) + "（稍后重试会更准）。"
    except Exception:
        remediation_note = ""

    return dedent(
        f"""
        [Reddit Signal Scanner] 勘探简报（C_scouting）

        ## 已分析赛道
        - 赛道：{task_summary.product_description.strip()}
        - 关键词：{", ".join([str(x) for x in keywords if x])}
        - 数据范围：
          - 社区：{len(community_names)} 个
          - 帖子：{posts_analyzed} 条（缓存命中率 {cache_hit_rate:.0%}）
          - 评论：{comments_analyzed} 条（状态：{comments_status}）

        ## 决策卡片
        1) 需求趋势：目前样本主要集中在 {len(community_names)} 个社区，热度需要继续观察。
        2) 问题/解决方案比（P/S）：约 {ps_ratio}（先当“方向感”，别当结论）。
        3) 核心战场：{", ".join(community_names[:4]) or "待补充"}。
        4) 下一步建议：扩充样本（更多社区/更长时间窗/更明确关键词），再升级到 B/A 报告。{remediation_note}
        {warning_block}

        ## 核心战场推荐
        {battlefields}

        ## 备注
        目前样本只够做“前期观察”，还不足以输出完整的痛点/机会结论；等样本更充分后，会自动升级为 B/A 报告。
        """
    ).strip()


async def _render_report_with_llm(
    *,
    task: TaskSummary,
    facts_slice: Mapping[str, Any] | None,
    report_tier: str,
    settings: Settings,
) -> str | None:
    if report_tier in {"C_scouting", "X_blocked"}:
        return None
    if not settings.enable_llm_summary:
        return None
    api_key = str(getattr(settings, "openai_api_key", "")).strip()
    if not api_key:
        return None
    if not facts_slice:
        return None

    facts_text = format_facts_for_prompt(facts_slice)
    prompt = build_complete_report_v9(task.product_description, facts_text)
    client = OpenAIChatClient(model=settings.llm_model_name, timeout=60.0, api_key=api_key)
    content = await client.generate(prompt, max_tokens=4000, temperature=0.25)
    return content.strip() or None


def _extract_json_payload(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    if "```" in text:
        lines = []
        in_block = False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                lines.append(line)
        text = "\n".join(lines).strip() if lines else text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def _render_structured_report_with_llm(
    *,
    task: TaskSummary,
    facts_slice: Mapping[str, Any] | None,
    report_tier: str,
    settings: Settings,
) -> dict[str, Any] | None:
    if report_tier in {"C_scouting", "X_blocked"}:
        return None
    if not settings.enable_llm_summary:
        return None
    if str(settings.llm_model_name).strip() == "local-extractive":
        return None
    api_key = str(getattr(settings, "openai_api_key", "")).strip()
    if not api_key:
        return None
    if not facts_slice:
        return None

    facts_text = format_facts_for_prompt(facts_slice)
    prompt = build_report_structured_prompt_v9(task.product_description, facts_text)
    client = OpenAIChatClient(model=settings.llm_model_name, timeout=60.0, api_key=api_key)
    raw = await client.generate(prompt, max_tokens=4000, temperature=0.25)
    return _extract_json_payload(raw)


async def run_analysis(
    task: TaskSummary,
    *,
    data_collection: DataCollectionService | None = None,
) -> AnalysisResult:
    topic_profile: TopicProfile | None = None
    topic_profile_id = getattr(task, "topic_profile_id", None)
    if topic_profile_id:
        profiles = load_topic_profiles()
        if not profiles:
            raise ValueError("TopicProfile config missing (config/topic_profiles.yaml)")
        topic_profile = match_topic_profile(str(topic_profile_id), profiles)
        if topic_profile is None:
            raise ValueError(f"Unknown topic_profile_id={topic_profile_id!r}")
        topic_profile_id = topic_profile.id.strip().lower()

    blacklist_config = get_blacklist_config()

    keywords = _extract_keywords(task.product_description)
    keywords = _augment_keywords(keywords, task.product_description)
    keywords = _apply_keyword_stopwords(keywords, blacklist_config)
    fetch_keywords = list(keywords)

    if topic_profile is not None:
        keywords = build_search_keywords(topic_profile, task.product_description)
        keywords = _augment_keywords(keywords, task.product_description)
        keywords = _apply_keyword_stopwords(keywords, blacklist_config)
        fetch_keywords = build_fetch_keywords(topic_profile, task.product_description)
        fetch_keywords = _augment_keywords(fetch_keywords, task.product_description)
        fetch_keywords = _apply_keyword_stopwords(fetch_keywords, blacklist_config)
        if not fetch_keywords:
            fetch_keywords = list(keywords)

    lookback_days = SAMPLE_LOOKBACK_DAYS
    if topic_profile is not None and topic_profile.preferred_days is not None:
        try:
            preferred = int(topic_profile.preferred_days)
        except Exception:
            preferred = 0
        if preferred > 0:
            lookback_days = preferred

    data_readiness: dict[str, Any] | None = None
    if topic_profile is not None:
        try:
            data_readiness = await _build_data_readiness_snapshot(topic_profile=topic_profile)
        except Exception:  # pragma: no cover - best effort
            data_readiness = None

    sample_result = await _run_sample_guard(
        keywords, task.product_description, lookback_days=lookback_days
    )
    if sample_result and sample_result.remaining_shortfall > 0:
        remediation_actions = await _schedule_auto_backfill_for_insufficient_samples(
            task=task,
            topic_profile=topic_profile,
        )
        blocked = _build_insufficient_sample_result(
            task, sample_result, lookback_days=lookback_days
        )
        if data_readiness is not None:
            blocked.sources["data_readiness"] = data_readiness
        if remediation_actions:
            blocked.sources["remediation_actions"] = remediation_actions
        blocked.sources["data_lineage"] = _build_data_lineage(
            source_range={
                "posts": int(sample_result.combined_count or 0),
                "comments": 0,
            },
            coverage=None,
            remediation_actions=remediation_actions,
        )
        return blocked

    settings = get_settings()
    # 禁用 mock 回退，只有显式打开 allow_mock_fallback 且非标准/高级质量时才允许使用演示数据
    allow_mock_fallback = False
    try:
        level = str(getattr(settings, "report_quality_level", "standard")).lower()
        if level not in {"standard", "premium"}:
            allow_mock_fallback = bool(settings.allow_mock_fallback and settings.enable_mock_data)
    except Exception:
        allow_mock_fallback = False
    data_source_label = "real"

    # 1) 从数据库加载真实的社区池
    from app.models.community_pool import CommunityPool as CommunityPoolModel

    db_communities: List[CommunityProfile] = []
    try:
        async with SessionFactory() as db:
            result = await db.execute(
                select(CommunityPoolModel)
                .where(CommunityPoolModel.is_active == True)
                .order_by(_community_pool_priority_order(CommunityPoolModel).desc())
                .limit(10)  # 优化：从 50 减少到 10，减少数据库查询和后续处理时间
            )
            communities = result.scalars().all()

            def _safe_categories(obj) -> list[str]:
                raw = getattr(obj, "categories", None)
                if isinstance(raw, dict):
                    return list(raw.keys())
                if isinstance(raw, list):
                    return [str(x) for x in raw]
                return []

            def _safe_desc(obj) -> dict:
                raw = getattr(obj, "description_keywords", None)
                if isinstance(raw, dict):
                    return raw
                return {}

            def _hybrid_weight(obj) -> float:
                cats = set(_safe_categories(obj))
                desc = _safe_desc(obj)
                base = 0.0
                if "crossborder:hybrid" in cats:
                    base += 1.0
                try:
                    base += float(desc.get("score", 0.0))
                except Exception:
                    pass
                try:
                    base += float(getattr(obj, "quality_score", 0.0)) * 0.5
                except Exception:
                    pass
                return float(base)

            # 轻权重排序：优先 hybrid_scoring + 高分 + 质量分
            try:
                communities.sort(key=_hybrid_weight, reverse=True)
            except Exception:
                pass

            # 层级均衡（若存在 categories 中的 layer 标签）
            layered: dict[str, list] = {"L1": [], "L2": [], "L3": [], "L4": []}
            rest: list = []
            for comm in communities:
                cats = set(_safe_categories(comm))
                assigned = False
                for code in ("L1", "L2", "L3", "L4"):
                    if f"layer:{code}" in cats:
                        layered[code].append(comm)
                        assigned = True
                        break
                if not assigned:
                    rest.append(comm)

            def _round_robin(groups: dict[str, list], fallback: list, limit: int = 10) -> list:
                order = ["L1", "L2", "L3", "L4"]
                out = []
                idx = 0
                while len(out) < limit and any(groups[k] for k in order) or fallback:
                    key = order[idx % len(order)]
                    if groups.get(key):
                        out.append(groups[key].pop(0))
                    elif fallback:
                        out.append(fallback.pop(0))
                    idx += 1
                    if idx > limit * 4:
                        break
                return out

            balanced = _round_robin(layered, rest, limit=10)
            if balanced:
                communities = balanced

            for comm in communities:
                # 提前获取所有属性，避免 session 过期
                name = comm.name
                # categories 和 description_keywords 在数据库中是 JSON (dict)
                # 需要转换为 list
                categories_raw = comm.categories or {}
                keywords_raw = comm.description_keywords or {}

                categories: list[str] = (
                    list(categories_raw.keys()) if isinstance(categories_raw, dict) else (list(categories_raw) if isinstance(categories_raw, list) else [])
                )
                keywords_list: list[str] = (
                    list(keywords_raw.keys()) if isinstance(keywords_raw, dict) else []
                )

                db_communities.append(
                    CommunityProfile(
                        name=name,
                        categories=tuple(categories) if categories else ("general",),
                        description_keywords=tuple(keywords_list)
                        if keywords_list
                        else tuple(keywords[:3]),
                        daily_posts=comm.daily_posts or 100,
                        avg_comment_length=comm.avg_comment_length or 70,
                        cache_hit_rate=0.8,
                    )
                )
    except Exception as e:
        logger.warning(f"Failed to load communities from database: {e}")
        db_communities = []

    # 2) 使用组合查询提高搜索精度
    # 注意：如果 data_collection 参数被显式提供（测试场景），跳过 Reddit 搜索
    search_posts: List[RedditPost] = []
    reddit_search_success = False
    try:
        if (
            data_collection is None  # 只有在没有显式提供 data_collection 时才执行 Reddit 搜索
            and settings.enable_reddit_search
            and settings.reddit_client_id
            and settings.reddit_client_secret
        ):
            reddit = RedditAPIClient(
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
                rate_limit=min(30, settings.reddit_rate_limit),
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=min(20.0, settings.reddit_request_timeout_seconds),
                max_concurrency=2,
            )
            async with reddit:
                # 使用组合查询而不是单个关键词
                query_keywords = keywords or fetch_keywords
                combined_queries = _build_reddit_search_queries(
                    tokens=query_keywords,
                    lookback_days=int(lookback_days),
                )
                search_time_filter = "month"
                if int(lookback_days) >= 540:
                    search_time_filter = "all"
                elif int(lookback_days) >= 365:
                    search_time_filter = "year"

                for q in combined_queries:
                    try:
                        logger.info(f"Searching Reddit with query: {q}")
                        items = await reddit.search_posts(
                            query=q,
                            limit=50,
                            time_filter=search_time_filter,
                            sort="relevance",
                        )
                        search_posts.extend(items)
                        logger.info(f"Found {len(items)} posts for query: {q}")
                    except Exception as e:
                        logger.warning(f"Reddit search failed for query '{q}': {e}")
                        continue

                if search_posts:
                    reddit_search_success = True
                    logger.info(
                        f"Total Reddit search results: {len(search_posts)} posts"
                    )
    except Exception as e:
        logger.warning(f"Reddit API initialization failed: {e}")
        search_posts = []

    # 3) 基于搜索结果和数据库社区池选择最相关的社区
    discovered_selected: List[CommunityProfile] = []

    # 合并所有可用的社区池（数据库 + 静态 COMMUNITY_CATALOGUE）
    base_communities: List[CommunityProfile] = db_communities + COMMUNITY_CATALOGUE
    if blacklist_config is not None:
        base_communities = [
            c
            for c in base_communities
            if not blacklist_config.is_community_blacklisted(c.name)
        ]
    if topic_profile is not None:
        # 有 TopicProfile 时，以 profile 的社区范围为准（避免被 mode 的粗粒度过滤“误杀”）
        base_communities = [
            c
            for c in base_communities
            if topic_profile_allows_community(topic_profile, c.name)
        ]

        allowlisted = [
            _normalise_community_name(c)
            for c in (topic_profile.allowed_communities or [])
        ]
        existing = {_normalise_community_name(c.name) for c in base_communities}
        for comm in [c for c in allowlisted if c and c not in existing][:20]:
            base_communities.append(
                CommunityProfile(
                    name=comm,
                    categories=("profile_seed",),
                    description_keywords=tuple(keywords[:6]) if keywords else ("profile",),
                    daily_posts=80,
                    avg_comment_length=70,
                    cache_hit_rate=0.5,
                )
            )
        all_communities = list(base_communities)
        if not all_communities:
            raise ValueError(f"TopicProfile {topic_profile.id!r} matches no communities.")
    else:
        all_communities = _filter_communities_by_mode(
            base_communities, getattr(task, "mode", "market_insight")
        )
    if not all_communities:
        raise InsufficientDataError(
            f"No eligible communities for mode={getattr(task, 'mode', 'market_insight')!r}"
        )

    # 创建社区名称映射（支持 "r/name" 和 "name" 两种格式）
    community_map: Dict[str, CommunityProfile] = {}
    for community_profile in all_communities:
        # 添加完整名称（如 "r/CryptoCurrency"）
        community_map[community_profile.name] = community_profile
        # 添加简短名称（如 "CryptoCurrency"）
        if community_profile.name.startswith("r/"):
            short_name = community_profile.name[2:]  # 去掉 "r/" 前缀
            community_map[short_name] = community_profile

    semantic_counts: dict[str, int] = {}
    try:
        async with SessionFactory() as db:
            semantic_counts = await fetch_topic_relevant_communities(
                db,
                topic=task.product_description,
                topic_tokens=keywords,
                exclusion_tokens=(
                    topic_profile_blocklist_keywords(topic_profile)
                    if topic_profile is not None
                    else None
                ),
                days=int(lookback_days),
                min_relevance_score=5,
            )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Semantic DB search skipped: %s", exc)
        semantic_counts = {}

    if search_posts:
        counter = Counter(p.subreddit for p in search_posts)
        logger.info(f"Discovered subreddits: {dict(counter.most_common(20))}")

        for name, count in counter.most_common(20):
            normalized = _normalise_community_name(name)
            if blacklist_config is not None and blacklist_config.is_community_blacklisted(normalized):
                continue
            # 尝试匹配社区（支持 "r/name" 和 "name" 两种格式）
            matched_comm = community_map.get(name) or community_map.get(f"r/{name}")

            if matched_comm:
                # 使用已知社区的信息
                if matched_comm not in discovered_selected:
                    discovered_selected.append(matched_comm)
                    logger.info(
                        f"Matched known community: {matched_comm.name} (count: {count})"
                    )
            else:
                # 新发现的社区
                new_comm = CommunityProfile(
                    name=f"r/{name}" if not name.startswith("r/") else name,
                    categories=("discovered",),
                    description_keywords=tuple(keywords[:6]),
                    daily_posts=80,
                    avg_comment_length=70,
                    cache_hit_rate=0.5,
                )
                discovered_selected.append(new_comm)
                logger.info(
                    f"Discovered new community: {new_comm.name} (count: {count})"
                )

        if topic_profile is None:
            discovered_selected = _filter_communities_by_mode(
                discovered_selected, getattr(task, "mode", "market_insight")
            )
        else:
            discovered_selected = [
                c
                for c in discovered_selected
                if topic_profile_allows_community(topic_profile, c.name)
            ]

    if semantic_counts:
        for name, count in sorted(
            semantic_counts.items(), key=lambda x: x[1], reverse=True
        )[:20]:
            normalized = _normalise_community_name(name)
            if topic_profile is not None and not topic_profile_allows_community(
                topic_profile, normalized
            ):
                continue
            if (
                blacklist_config is not None
                and blacklist_config.is_community_blacklisted(normalized)
            ):
                continue
            matched_comm = (
                community_map.get(name)
                or community_map.get(normalized)
                or community_map.get(f"r/{name}")
            )
            if matched_comm:
                if matched_comm not in discovered_selected:
                    discovered_selected.append(matched_comm)
                    logger.info(
                        f"Matched semantic community: {matched_comm.name} (count: {count})"
                    )
            else:
                new_comm = CommunityProfile(
                    name=normalized,
                    categories=("semantic",),
                    description_keywords=tuple(keywords[:6])
                    if keywords
                    else ("semantic",),
                    daily_posts=80,
                    avg_comment_length=70,
                    cache_hit_rate=0.5,
                )
                discovered_selected.append(new_comm)
                logger.info(
                    f"Discovered semantic community: {new_comm.name} (count: {count})"
                )

    # 4) 如果搜索结果不足，从社区池中补充
    if len(discovered_selected) < 10:
        logger.info(
            f"Discovered communities insufficient ({len(discovered_selected)}), supplementing from community pool..."
        )
        scored_communities: list[tuple[CommunityProfile, float]] = [
            (c, _score_community(keywords, c)) for c in all_communities
        ]
        scored_communities.sort(key=lambda x: x[1], reverse=True)

        for community_profile, community_score in scored_communities[:15]:
            if community_profile not in discovered_selected:
                discovered_selected.append(community_profile)
                logger.info(
                    f"Added community from pool: {community_profile.name} (score: {community_score:.2f})"
                )
            if len(discovered_selected) >= 12:
                break

    # 5) 如果仍然没有社区，使用静态社区池
    selected = (
        discovered_selected
        if discovered_selected
        else _select_top_communities(keywords)
    )

    logger.info(f"Final selected communities: {[c.name for c in selected]}")

    collection_result: CollectionResult | None = None
    cache_only_result: CollectionResult | None = None
    service = data_collection
    close_reddit = False
    if service is None:
        service = _build_data_collection_service(settings)
        close_reddit = service is not None

    api_call_count: int | None = None
    api_failure_details: list[dict[str, str]] = []
    stale_cache_subreddits: set[str] = set()
    stale_cache_fallback_subreddits: set[str] = set()

    if search_posts:
        posts_by_subreddit = _group_search_posts_by_selected_subreddit(
            search_posts=search_posts,
            selected=selected,
        )
        total_posts = sum(len(v) for v in posts_by_subreddit.values())
        cached: set[str] = set()
        collection_result = CollectionResult(
            total_posts=total_posts,
            cache_hits=len(cached),
            api_calls=0,
            # Reddit search 是 API 直出，不是缓存命中；这里宁可写 0.0，也不要假装 90% 命中。
            cache_hit_rate=0.0,
            posts_by_subreddit=posts_by_subreddit,
            cached_subreddits=cached,
        )
    elif service is not None:
        try:
            collection_result = await service.collect_posts(
                [profile.name for profile in selected],
                limit_per_subreddit=50,  # 优化：从 100 减少到 50，减少数据处理时间
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "[降级策略] Data collection from Reddit API failed (error: %s). "
                "Falling back to synthetic data.",
                exc,
                exc_info=True,
            )
            collection_result = None
    else:
        logger.info(
            "[降级策略] No Reddit API service available. "
            "Attempting cache-only collection for %d communities.",
            len(selected),
        )
        cache_only_result = await _try_cache_only_collection(selected, settings)

    collected: List[CollectedCommunity] = []
    cache_hit_rate: float | None = None
    total_cache_hits = 0
    total_cache_misses = 0
    total_posts = 0
    api_call_count = 0

    if collection_result is not None:
        collected, _, _, _ = _collection_from_result(selected, collection_result)
        cache_hit_rate = collection_result.cache_hit_rate
        api_call_count = collection_result.api_calls
        api_failure_details = list(collection_result.api_failures)
        stale_cache_subreddits = set(collection_result.stale_cache_subreddits)
        stale_cache_fallback_subreddits = set(
            collection_result.stale_cache_fallback_subreddits
        )
    elif cache_only_result is not None:
        collected, _, _, _ = _collection_from_result(selected, cache_only_result)
        cache_hit_rate = cache_only_result.cache_hit_rate
        data_source_label = "cache"
        api_failure_details = list(cache_only_result.api_failures)
        stale_cache_subreddits = set(cache_only_result.stale_cache_subreddits)
        stale_cache_fallback_subreddits = set(
            cache_only_result.stale_cache_fallback_subreddits
        )
    else:
        raise InsufficientDataError("No real data found!")

    # 合同C/Phase105-106：真实链路不允许用“演示合成帖”填空，否则会出现：
    # - 赛道看起来命中了（关键词），但其实不是 Reddit 原帖
    # - comments 永远拿不到（post_id 不是 Reddit id），自愈闭环失效
    # 只有在显式允许 mock/demo 回退时才允许注入合成数据。
    if allow_mock_fallback:
        collected = _backfill_cache_misses(collected, keywords)
    total_cache_hits = sum(entry.cache_hits for entry in collected)
    total_cache_misses = sum(entry.cache_misses for entry in collected)
    total_posts = total_cache_hits + total_cache_misses

    if total_posts:
        cache_hit_rate = total_cache_hits / total_posts
    else:
        cache_hit_rate = cache_hit_rate or 0.0

    all_posts = [post for entry in collected for post in entry.posts]
    hybrid_posts: list[dict[str, Any]] = []
    if settings.enable_hybrid_retrieval:
        try:
            async with SessionFactory() as _session:
                hybrid_posts = await fetch_hybrid_posts(
                    _session,
                    topic=task.product_description,
                    topic_tokens=fetch_keywords or keywords,
                    days=int(lookback_days),
                    limit=int(settings.hybrid_post_limit),
                    vector_distance=float(settings.hybrid_vector_distance),
                    hybrid_weight=float(settings.hybrid_weight),
                )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Hybrid retrieval skipped: %s", exc)

    if hybrid_posts:
        all_posts = _merge_posts_by_id(all_posts, hybrid_posts)

    filter_keywords = fetch_keywords if topic_profile is not None else keywords
    filtered_posts = _filter_posts_by_keywords(all_posts, filter_keywords)
    filtered_posts = _filter_posts_by_blacklist_config(filtered_posts, blacklist_config)
    if topic_profile is not None:
        filtered_posts = _filter_posts_by_blocklist(
            filtered_posts, topic_profile_blocklist_keywords(topic_profile)
        )
        filtered_posts = _apply_topic_profile_required_filter(filtered_posts, topic_profile)
        filtered_posts = _apply_topic_profile_context_filter(filtered_posts, topic_profile)
    deduped_posts = deduplicate_posts(filtered_posts)

    post_remediation_actions: list[dict[str, Any]] = []
    analysis_blocked_reason: str | None = None

    # Contract B (topic-level preflight):
    # If a narrow topic's "double-key" filter yields too few posts, treat it as insufficient_samples and auto backfill
    # instead of proceeding to produce an X_blocked facts package (which looks like a failure but doesn't self-heal).
    if topic_profile is not None:
        min_posts = 20
        try:
            pain_floor = int(topic_profile.pain_min_mentions or 0)
        except Exception:
            pain_floor = 0
        if pain_floor > 0:
            min_posts = max(10, pain_floor * 2)

        if len(deduped_posts) < min_posts:
            post_remediation_actions = await _schedule_auto_backfill_for_insufficient_samples(
                task=task,
                topic_profile=topic_profile,
            )
            analysis_blocked_reason = "insufficient_samples"

            # If literally no posts pass the "double-key" filter, stop here and wait for warmup.
            # Otherwise we still proceed to generate a scouting report (C_scouting), while keeping
            # the warmup flag + remediation actions so the system can auto-rerun and upgrade later.
            if len(deduped_posts) == 0:
                sources: Dict[str, Any] = {
                    "communities": [c.name for c in selected],
                    "posts_analyzed": int(len(deduped_posts)),
                    "comments_analyzed": 0,
                    "counts_analyzed": {"posts": int(len(deduped_posts)), "comments": 0},
                    "counts_db": {
                        "posts_current": int(len(deduped_posts)),
                        "comments_total": 0,
                        "comments_eligible": 0,
                    },
                    "comments_pipeline_status": "disabled",
                    "cache_hit_rate": round(float(cache_hit_rate or 0.0), 2),
                    "product_description": task.product_description,
                    "mode": getattr(task, "mode", "market_insight"),
                    "topic_profile_id": getattr(task, "topic_profile_id", None),
                    "analysis_blocked": "insufficient_samples",
                    "data_source": data_source_label,
                    "lookback_days": int(lookback_days),
                    "keywords": list(keywords),
                    "fetch_keywords": list(fetch_keywords),
                    "report_tier": "C_scouting",
                    "facts_v2_quality": {
                        "passed": True,
                        "tier": "C_scouting",
                        "flags": ["insufficient_samples"],
                        "metrics": {
                            "filtered_posts": int(len(deduped_posts)),
                            "min_required_posts": int(min_posts),
                            "lookback_days": int(lookback_days),
                        },
                    },
                }

                if data_readiness is not None:
                    sources["data_readiness"] = data_readiness
                if post_remediation_actions:
                    sources["remediation_actions"] = post_remediation_actions

                sources["data_lineage"] = _build_data_lineage(
                    source_range={"posts": int(len(deduped_posts)), "comments": 0},
                    coverage=None,
                    remediation_actions=post_remediation_actions,
                )

                report_html = dedent(
                    f"""
                    <html>
                      <body>
                        <h1>分析暂停：样本不足</h1>
                        <p>这是一个窄题（{topic_profile.topic_name}）。</p>
                        <p>在“锚点词 + 语境词”的双钥匙过滤后，只剩 <strong>{len(deduped_posts)}</strong> 条帖子，未达到本次最低门槛 {min_posts} 条。</p>
                        <p>系统已自动下单补量（回填抓取）。稍后会自动重跑；如果你很急，可以扩社区/延长时间窗/补充更明确的关键词。</p>
                      </body>
                    </html>
                    """
                ).strip()

                return AnalysisResult(
                    insights={"pain_points": [], "competitors": [], "opportunities": [], "action_items": []},
                    sources=sources,
                    report_html=report_html,
                    action_items=[],
                    confidence_score=0.0,
                )

    post_score_stats: dict[str, Any] = {}
    noise_pool_stats: dict[str, Any] = {}
    embedding_map: dict[str, list[float]] = {}
    try:
        async with SessionFactory() as session:
            deduped_posts, post_score_stats = await _attach_post_scores(
                session, deduped_posts
            )
            if settings.enable_vector_dedup:
                embedding_map = await _fetch_post_embeddings(session, deduped_posts)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Post score attach skipped: %s", exc)
    if settings.enable_vector_dedup and embedding_map:
        deduped_posts = deduplicate_posts_by_embeddings(
            deduped_posts,
            embedding_map,
            threshold=float(settings.vector_dedup_threshold),
        )
    duplicate_summary = [
        {
            "post_id": post.get("id"),
            "duplicate_ids": post.get("duplicate_ids", []),
            "evidence_count": post.get("evidence_count", 1),
        }
        for post in deduped_posts
        if post.get("duplicate_ids")
    ]
    deduped_posts, noise_pool_stats = _apply_post_score_policy(deduped_posts)
    dedup_stats = get_last_stats()
    numeric_ids: list[int] = []
    for post in deduped_posts:
        pid_raw = str(post.get("id", "")).strip()
        if pid_raw.isdigit():
            try:
                numeric_ids.append(int(pid_raw))
            except Exception:
                continue

    business_signals = await _extract_business_signals_from_labels(numeric_ids)
    if business_signals is None:
        logger.debug("Label-based signals unavailable; falling back to heuristic extraction.")
        business_signals = SIGNAL_EXTRACTOR.extract(deduped_posts, keywords)
    else:
        logger.info(
            "Using content_labels/content_entities for signal extraction (posts=%d).",
            len(numeric_ids),
        )

    post_lookup: Dict[str, Dict[str, Any]] = {
        str(post.get("id", "")): post for post in deduped_posts if post.get("id")
    }

    def _post_content(payload: Mapping[str, Any]) -> str:
        for key in ("summary", "title", "selftext", "text", "body"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def build_example_posts(source_ids: Sequence[str]) -> List[Dict[str, Any]]:
        """Select up to 3 example posts with preference for distinct communities.

        Guarantees at least 2 examples whenever possible by supplementing from
        the global deduped_posts (sorted by score) if source_ids are insufficient
        or map to missing payloads.
        """
        examples: List[Dict[str, Any]] = []
        seen_communities: set[str] = set()

        # 1) First pass: follow source_ids, prefer distinct communities
        for post_id in source_ids or []:
            payload = post_lookup.get(str(post_id))
            if not payload:
                continue
            community = str(payload.get("subreddit", "")).strip()
            if community and not community.lower().startswith("r/"):
                community = f"r/{community}"
            content = _post_content(payload)
            if not content:
                continue
            if community and community in seen_communities:
                # try to keep diversity; allow duplicates only if we still need items
                if len(examples) >= 2:
                    continue
            example = {
                "community": community,
                "content": content,
                "upvotes": int(payload.get("score", 0) or 0),
                "url": payload.get("url"),
                "author": payload.get("author"),
                "permalink": payload.get("permalink"),
                "evidence_count": int(payload.get("evidence_count", 1) or 1),
                "duplicate_ids": payload.get("duplicate_ids", []),
            }
            examples.append(example)
            if community:
                seen_communities.add(community)
            if len(examples) >= 3:
                break

        # 2) Supplement: ensure at least 2 examples
        if len(examples) < 2:
            # Pick top-scored posts not already selected
            selected_ids = {pid for pid in (source_ids or [])}
            candidates = [
                p for p in deduped_posts
                if str(p.get("id", "")) not in selected_ids
                and (p.get("url") or p.get("permalink"))
            ]
            try:
                candidates.sort(key=lambda x: int(x.get("score", 0) or 0), reverse=True)
            except Exception:
                pass
            for payload in candidates:
                community = str(payload.get("subreddit", "")).strip()
                if community and not community.lower().startswith("r/"):
                    community = f"r/{community}"
                content = _post_content(payload)
                if not content:
                    continue
                if community and community in seen_communities and len(examples) >= 1:
                    # keep some diversity if we already have one
                    continue
                examples.append(
                    {
                        "community": community,
                        "content": content,
                        "upvotes": int(payload.get("score", 0) or 0),
                        "url": payload.get("url"),
                        "author": payload.get("author"),
                        "permalink": payload.get("permalink"),
                        "evidence_count": int(payload.get("evidence_count", 1) or 1),
                        "duplicate_ids": payload.get("duplicate_ids", []),
                    }
                )
                if community:
                    seen_communities.add(community)
                if len(examples) >= 2:
                    break

        return examples

    def build_user_examples(source_ids: Sequence[str]) -> List[str]:
        quotes: List[str] = []
        seen: set[str] = set()
        for post_id in source_ids:
            payload = post_lookup.get(str(post_id))
            if not payload:
                continue
            text = _post_content(payload)
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            quotes.append(text)
            if len(quotes) >= 3:
                break
        return quotes

    def classify_competitor_sentiment(value: float) -> str:
        if value < -0.15:
            return "negative"
        if abs(value) <= 0.15:
            return "mixed"
        return "positive"

    def competitor_attributes(label: str) -> tuple[List[str], List[str]]:
        if label == "negative":
            return ["行业认知度高"], ["用户反馈偏负面"]
        if label == "positive":
            return ["用户反馈积极", "社区认可度高"], ["需要继续观察长期表现"]
        return ["社区讨论热度高"], ["等待更多反馈细节"]

    pain_points_payload: List[Dict[str, Any]] = []
    for pain_signal in business_signals.pain_points:
        severity = _classify_pain_severity(pain_signal.frequency, pain_signal.sentiment)
        pain_points_payload.append(
            {
                "description": pain_signal.description,
                "frequency": pain_signal.frequency,
                "sentiment_score": round(pain_signal.sentiment, 2),
                "severity": severity,
                "example_posts": build_example_posts(pain_signal.source_posts),
                "user_examples": build_user_examples(pain_signal.source_posts),
            }
        )

    pain_counts_by_community: Dict[str, int] = {}
    for pain_signal in business_signals.pain_points:
        for pid in pain_signal.source_posts:
            payload = post_lookup.get(pid)
            if not payload:
                continue
            community = str(payload.get("subreddit", "")).strip()
            if not community:
                continue
            variants = {community}
            if not community.lower().startswith("r/"):
                variants.add(f"r/{community}")
            for name in variants:
                pain_counts_by_community[name] = pain_counts_by_community.get(name, 0) + 1

    total_competitor_mentions = (
        sum(comp_signal.mention_count for comp_signal in business_signals.competitors)
        or 1
    )
    competitor_sentiment_totals: Counter[str] = Counter()
    competitors_payload: List[Dict[str, Any]] = []
    for competitor_signal in business_signals.competitors:
        sentiment_label = classify_competitor_sentiment(competitor_signal.sentiment)
        competitor_sentiment_totals[sentiment_label] += competitor_signal.mention_count
        strengths, weaknesses = competitor_attributes(sentiment_label)
        competitors_payload.append(
            {
                "name": competitor_signal.name,
                "mentions": competitor_signal.mention_count,
                "sentiment": sentiment_label,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "market_share": int(
                    round(
                        (competitor_signal.mention_count / total_competitor_mentions)
                        * 100
                    )
                ),
                "context_snippets": competitor_signal.context_snippets[:3],
            }
        )

    competitors_payload = assign_competitor_layers(competitors_payload)

    # Prepare helper views for linking
    clusters = []
    try:
        # Prefer DB 聚合（content_labels），不足时回落 TF-IDF
        from app.services.analysis.pain_cluster import cluster_pain_points_auto

        async with SessionFactory() as _s:
            clusters = await cluster_pain_points_auto(
                _s,
                since_days=int(lookback_days),
                subreddits=[c.replace("r/", "").lower() for c in sources.get("communities", [])] if isinstance(sources, Mapping) else None,
                limit_per_source=_GUARD_SAMPLE_LIMIT,
                fallback_items=pain_points_payload,
                min_clusters=2,
                max_clusters=5,
            )
        if not clusters:
            clusters = cluster_pain_points(pain_points_payload)
    except Exception:
        try:
            clusters = cluster_pain_points(pain_points_payload)
        except Exception:
            clusters = insights.get("pain_clusters", []) or []

    channel_names: List[str] = []
    try:
        channel_names = [row.get("name") for row in insights.get("channel_breakdown", []) if isinstance(row, Mapping) and row.get("name")]
    except Exception:
        channel_names = []

    def _link_pain_cluster(desc: str) -> str | None:
        try:
            lower = (desc or "").lower()
            best = None
            for entry in clusters:
                topic = str(entry.get("topic") or "").strip()
                if topic and topic.lower() in lower:
                    best = topic
                    break
            if best is None and clusters:
                best = str(clusters[0].get("topic") or "")
            return best
        except Exception:
            return None

    opportunities_payload: List[Dict[str, Any]] = []
    for opportunity_signal in business_signals.opportunities:
        key_insights = (
            opportunity_signal.keywords[:4] if opportunity_signal.keywords else []
        )
        if not key_insights:
            key_insights = [opportunity_signal.description]
        linked_cluster = _link_pain_cluster(opportunity_signal.description)
        top_channels = channel_names[:3] if channel_names else []
        opportunities_payload.append(
            {
                "description": opportunity_signal.description,
                "relevance_score": round(opportunity_signal.relevance, 2),
                "potential_users": f"约{opportunity_signal.potential_users}个潜在团队",
                "potential_users_est": int(opportunity_signal.potential_users),
                "linked_pain_cluster": linked_cluster,
                "top_channels": top_channels,
                "key_insights": key_insights,
                "source_examples": build_example_posts(opportunity_signal.source_posts),
            }
        )

    ps_ratio_value = business_signals.ps_ratio
    if ps_ratio_value is None:
        pain_total = sum(int(p.get("frequency") or 0) for p in pain_points_payload)
        solution_total = sum(
            int(getattr(opportunity_signal, "potential_users", 0) or 0)
            for opportunity_signal in business_signals.opportunities
        )
        if solution_total > 0:
            ps_ratio_value = pain_total / solution_total
        elif pain_total > 0:
            ps_ratio_value = float(pain_total)
        else:
            ps_ratio_value = 0.0

    insights = {
        "pain_points": pain_points_payload,
        "competitors": competitors_payload,
        "opportunities": opportunities_payload,
    }
    insights["pain_clusters"] = clusters or cluster_pain_points(pain_points_payload)

    action_reports = [
        report.to_dict() for report in build_opportunity_reports(insights)
    ]
    insights["action_items"] = action_reports
    # Entity summary via new pipeline (folder-based dictionaries); fallback to matcher
    try:
        entity_summary = ENTITY_PIPELINE.summarize(insights)
        insights["entity_summary"] = entity_summary
        channels = entity_summary.get("channels", []) if isinstance(entity_summary, Mapping) else []
        insights["channel_breakdown"] = [
            {
                "name": str(row.get("name")),
                "mentions": int(row.get("mentions") or 0),
            }
            for row in channels[:5]
            if isinstance(row, Mapping) and row.get("name")
        ]
    except Exception:  # defensive fallback
        entity_summary = ENTITY_MATCHER.summarize(insights)
        insights["entity_summary"] = entity_summary
        insights["channel_breakdown"] = []

    processing_seconds = int(30 + len(collected) * 6 + total_cache_misses * 2)
    processing_seconds = min(processing_seconds, 260)

    communities_detail: List[Dict[str, Any]] = []
    for entry in collected:
        entry_total_posts = entry.cache_hits + entry.cache_misses
        entry_hit_rate = (
            entry.cache_hits / entry_total_posts if entry_total_posts else 0.0
        )
        communities_detail.append(
            {
                "name": entry.profile.name,
                "categories": list(entry.profile.categories),
                "mentions": len(entry.posts),
                "daily_posts": entry.profile.daily_posts,
                "avg_comment_length": entry.profile.avg_comment_length,
                "cache_hit_rate": round(entry_hit_rate, 2),
                "from_cache": entry_hit_rate >= CACHE_HIT_RATE_TARGET,
            }
        )

    trend_series: list[dict[str, Any]] = []
    trend_tokens = list(dict.fromkeys(fetch_keywords or keywords))
    if trend_tokens:
        try:
            async with SessionFactory() as _s:
                trend_series = await build_trend_analysis(
                    _s,
                    topic_tokens=trend_tokens,
                    months=12,
                )
        except Exception:
            trend_series = []

    market_saturation_payload: list[dict[str, Any]] = []
    competitor_names = [
        str(row.get("name"))
        for row in competitors_payload
        if isinstance(row, Mapping) and row.get("name")
    ]
    if competitor_names and communities_detail:
        try:
            async with SessionFactory() as _s:
                matrix = SaturationMatrix()
                saturation_rows = await matrix.compute(
                    _s,
                    communities=[row.get("name") for row in communities_detail if row.get("name")],
                    brands=competitor_names[:10],
                    days=int(lookback_days) if lookback_days else None,
                )
            market_saturation_payload = build_market_saturation_payload(saturation_rows)
        except Exception:
            market_saturation_payload = []

    battlefield_profiles = build_battlefield_profiles(
        communities_detail=communities_detail,
        pain_points=pain_points_payload,
        pain_counts_by_community=pain_counts_by_community,
        limit=4,
    )
    top_drivers = build_top_drivers(pain_points_payload, action_items=action_reports, limit=3)

    insights["market_saturation"] = market_saturation_payload
    insights["battlefield_profiles"] = battlefield_profiles
    insights["top_drivers"] = top_drivers

    # 推断数据来源注记：若存在 "discovered" 类别，视为 pool+discovery；否则默认 pool
    seed_source = "pool+discovery" if any(
        ("discovered" in (entry.profile.categories or ())) for entry in collected
    ) else "pool"

    facts_v2_quality: dict[str, Any] | None = None
    report_tier: str | None = None
    facts_v2_package: dict[str, Any] | None = None
    topic_label = (
        topic_profile.topic_name
        if topic_profile is not None
        else str(task.product_description or "unknown")
    )
    topic_profile_id_value = topic_profile.id if topic_profile is not None else None

    comment_lookup: Dict[str, Dict[str, Any]] = {}

    def _unique_authors(source_ids: Sequence[str]) -> int:
        authors: set[str] = set()
        for pid in source_ids:
            payload = post_lookup.get(pid)
            author = ""
            if payload:
                author = str(payload.get("author") or "").strip()
            else:
                comment_payload = comment_lookup.get(pid) or {}
                author = str(
                    comment_payload.get("author")
                    or comment_payload.get("author_name")
                    or comment_payload.get("author_id")
                    or ""
                ).strip()
            author = author.lower()
            if author:
                authors.add(author)
        return len(authors)

    def _evidence_count(source_id: str) -> int:
        payload = post_lookup.get(source_id)
        if not payload:
            return 1
        raw = payload.get("evidence_count", 1)
        try:
            count = int(raw or 1)
        except (TypeError, ValueError):
            count = 1
        return max(1, count)

    def _evidence_ids(source_ids: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for pid in source_ids:
            payload = post_lookup.get(pid) or {}
            ids = payload.get("evidence_post_ids") or [pid]
            if not isinstance(ids, list):
                ids = [pid]
            for raw in ids:
                item = str(raw or "").strip()
                if not item or item in seen:
                    continue
                seen.add(item)
                out.append(item)
                if len(out) >= 50:
                    return out
        return out

    def _evidence_quote_ids(source_ids: Sequence[str]) -> list[str]:
        # 优先使用评论作为“原话证据”；其次才回退到帖子（避免“有评论但证据全是帖子”）。
        candidates: list[tuple[int, str]] = []
        for sid in source_ids:
            payload = comment_lookup.get(sid)
            if not payload:
                continue
            try:
                score = int(payload.get("score") or 0)
            except (TypeError, ValueError):
                score = 0
            candidates.append((score, sid))
        candidates.sort(key=lambda x: x[0], reverse=True)

        seen: set[str] = set()
        out: list[str] = []
        for _score, sid in candidates:
            if sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
            if len(out) >= 5:
                return out

        # fallback: allow post evidence ids if no comment evidence exists.
        for sid in _evidence_ids(source_ids):
            if sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
            if len(out) >= 5:
                break
        return out

    sample_posts_db = []
    try:
        ranked = sorted(
            deduped_posts,
            key=lambda p: int(p.get("score", 0) or 0),
            reverse=True,
        )
    except Exception:
        ranked = list(deduped_posts)
    for row in ranked[:50]:
        title = str(row.get("title") or "").strip()
        summary = str(row.get("summary") or "").strip()
        if not title and not summary:
            continue
        combined = f"{title} {summary}".strip()
        raw_subreddit = str(row.get("subreddit") or "").strip()
        subreddit = (
            _normalise_community_name(raw_subreddit) if raw_subreddit else "unknown"
        )
        sample_posts_db.append(
            {
                "title": combined,
                "text": combined,
                "body": summary,
                "subreddit": subreddit,
            }
        )

    # NOTE: high_value_pains / brand_pain / solutions 将在 sample_comments_db 加载后生成，
    # 以保证评论能真正进入证据链（Task 8 / P1）。

    # --- P0.5: comments must be part of the facts package (no more hard-coded 0) ---
    sample_comments_db: list[dict[str, Any]] = []
    comment_counts_by_subreddit: Counter[str] = Counter()
    posts_db_current: int = 0
    comments_db_total: int = 0
    comments_db_eligible: int = 0
    comments_pipeline_status: str = "unknown"
    try:
        source_ids = [
            str(post.get("id") or "").strip()
            for post in deduped_posts
            if str(post.get("id") or "").strip()
        ]
        unique_source_ids = list(dict.fromkeys(source_ids))
        if unique_source_ids:
            async with SessionFactory() as session:
                posts_row = await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM posts_raw p
                        WHERE p.source = 'reddit'
                          AND p.is_current = true
                          AND p.source_post_id = ANY(:source_ids)
                        """
                    ),
                    {"source_ids": unique_source_ids},
                )
                # DB 口径：这批帖子在库里一共有多少评论 / 可用评论（剔除删除/噪音/短文本）
                total_row = await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM comments c
                        WHERE c.source = 'reddit'
                          AND c.source_post_id = ANY(:source_ids)
                        """
                    ),
                    {"source_ids": unique_source_ids},
                )
                eligible_row = await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM comments c
                        WHERE c.source = 'reddit'
                          AND c.source_post_id = ANY(:source_ids)
                          AND COALESCE(c.is_deleted, false) = false
                          AND (c.business_pool IS NULL OR c.business_pool <> 'noise')
                          AND c.body IS NOT NULL
                          AND LENGTH(c.body) > 20
                        """
                    ),
                    {"source_ids": unique_source_ids},
                )
                try:
                    posts_db_current = int(posts_row.scalar_one() or 0)
                except Exception:
                    posts_db_current = 0
                try:
                    comments_db_total = int(total_row.scalar_one() or 0)
                except Exception:
                    comments_db_total = 0
                try:
                    comments_db_eligible = int(eligible_row.scalar_one() or 0)
                except Exception:
                    comments_db_eligible = 0

                result = await session.execute(
                    text(
                        """
                        SELECT
                            c.id AS comment_id,
                            c.body,
                            c.subreddit,
                            c.author_name,
                            c.permalink,
                            c.score,
                            c.source_post_id
                        FROM comments c
                        WHERE c.source = 'reddit'
                          AND c.source_post_id = ANY(:source_ids)
                          AND COALESCE(c.is_deleted, false) = false
                          AND (c.business_pool IS NULL OR c.business_pool <> 'noise')
                          AND c.body IS NOT NULL
                          AND LENGTH(c.body) > 20
                        ORDER BY c.score DESC NULLS LAST, c.created_utc DESC NULLS LAST
                        LIMIT 200
                        """
                    ),
                    {"source_ids": unique_source_ids},
                )
                for row in result.mappings().all():
                    body = str(row.get("body") or "").strip()
                    if not body:
                        continue
                    raw_subreddit = str(row.get("subreddit") or "").strip()
                    subreddit = (
                        _normalise_community_name(raw_subreddit)
                        if raw_subreddit
                        else "unknown"
                    )
                    sample_comments_db.append(
                        {
                            "id": str(row.get("comment_id") or ""),
                            "text": body,
                            "body": body,
                            "subreddit": subreddit,
                            "author": row.get("author_name"),
                            "permalink": row.get("permalink"),
                            "score": int(row.get("score") or 0),
                            "source_post_id": row.get("source_post_id"),
                        }
                    )
            # Apply the same "narrow topic context key" filter for comments when enabled.
            if topic_profile is not None and topic_profile.require_context_for_fetch:
                sample_comments_db = list(
                    filter_items_by_profile_context(
                        sample_comments_db,
                        topic_profile,
                        text_keys=("text", "body"),
                    )
                )
            sample_comments_db = sample_comments_db[:50]
            for item in sample_comments_db:
                raw_name = str(item.get("subreddit") or "").strip()
                name = _normalise_community_name(raw_name) if raw_name else "unknown"
                comment_counts_by_subreddit[name] += 1
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Sample comments fetch skipped: %s", exc)
        comments_pipeline_status = "disabled"

    comment_remediation_actions: list[dict[str, Any]] = []
    if topic_profile is not None and not sample_comments_db:
        # Contract B: 评论为 0 时，不要“假装能分析”，先自动下单补量（走 outbox）。
        try:
            comment_remediation_actions = await _schedule_auto_backfill_for_missing_comments(
                task=task,
                topic_profile=topic_profile,
                posts=deduped_posts,
            )
        except Exception as exc:  # pragma: no cover - best effort only
            logger.warning("Auto comment remediation skipped: %s", exc, exc_info=True)

    if sample_comments_db:
        comments_pipeline_status = "ok"
    elif comments_db_total <= 0:
        comments_pipeline_status = "disabled"
    elif comments_db_eligible <= 0:
        comments_pipeline_status = "all_noise"
    else:
        # 有可用评论，但被 topic_profile 的“语境双钥匙”筛掉了
        comments_pipeline_status = "filtered"

    # --- P1: comments participate in business signals & evidence chain ---
    comment_lookup = {
        str(item.get("id") or "").strip(): item
        for item in sample_comments_db
        if str(item.get("id") or "").strip()
    }
    comment_signal_inputs: list[dict[str, Any]] = []
    for cid, item in comment_lookup.items():
        body = str(item.get("text") or item.get("body") or "").strip()
        if not body:
            continue
        comment_signal_inputs.append(
            {
                "id": cid,
                "title": "",
                "summary": body,
                "score": item.get("score", 0),
                "num_comments": 0,
            }
        )

    comment_signals: BusinessSignals | None = None
    if comment_signal_inputs:
        try:
            comment_signals = SIGNAL_EXTRACTOR.extract(comment_signal_inputs, keywords)
        except Exception:  # pragma: no cover - defensive fallback
            comment_signals = None

    pains_for_facts = list(business_signals.pain_points)
    competitors_for_facts = list(business_signals.competitors)
    solutions_for_facts = list(getattr(business_signals, "solutions", []) or [])
    if comment_signals is not None:
        pains_for_facts.extend(comment_signals.pain_points)
        competitors_for_facts.extend(comment_signals.competitors)
        solutions_for_facts.extend(getattr(comment_signals, "solutions", []) or [])

    # Phase106: 将“句子级抱怨碎片”合并成少量痛点簇，否则 mentions/authors 永远过不了门槛 → 只能 C_scouting。
    high_value_pains = _cluster_pain_signals_for_facts(
        pains_for_facts,
        evidence_count=_evidence_count,
        unique_authors=_unique_authors,
        evidence_quote_ids=_evidence_quote_ids,
    )
    brand_pain = [
        {
            "name": str(comp.name or "").strip(),
            "mentions": int(comp.mention_count or 0),
            "unique_authors": _unique_authors(comp.source_posts),
            "evidence_quote_ids": _evidence_quote_ids(comp.source_posts),
        }
        for comp in competitors_for_facts
    ]
    solutions_block = [
        {
            "description": str(sol.description or "").strip(),
            "frequency": int(getattr(sol, "frequency", 0) or 0),
            "evidence_quote_ids": _evidence_quote_ids(sol.source_posts),
        }
        for sol in solutions_for_facts
    ]
    if not solutions_block:
        solutions_block = [
            {
                "description": str(op.description or "").strip(),
                "evidence_quote_ids": _evidence_quote_ids(op.source_posts),
            }
            for op in business_signals.opportunities
        ]

    subreddit_counts = Counter()
    for post in deduped_posts:
        raw_name = str(post.get("subreddit") or "").strip()
        name = _normalise_community_name(raw_name) if raw_name else "unknown"
        subreddit_counts[name] += 1
    aggregates = {
        "communities": [
            {
                "name": name,
                "posts": int(count),
                "comments": int(comment_counts_by_subreddit.get(name, 0)),
            }
            for name, count in subreddit_counts.most_common()
        ]
    }
    source_range = {"posts": len(deduped_posts), "comments": len(sample_comments_db)}
    all_remediation_actions: list[dict[str, Any]] = [
        *post_remediation_actions,
        *comment_remediation_actions,
    ]
    coverage_summary = await _fetch_coverage_summary(
        [entry.profile.name for entry in collected]
    )
    data_lineage = _build_data_lineage(
        source_range=source_range,
        coverage=coverage_summary,
        remediation_actions=all_remediation_actions,
    )
    data_lineage["counts_db"] = {
        "posts_current": int(posts_db_current),
        "comments_total": int(comments_db_total),
        "comments_eligible": int(comments_db_eligible),
    }
    data_lineage["comments_pipeline_status"] = comments_pipeline_status

    facts_v2_package = {
        "schema_version": "2.0",
        "meta": {
            "topic": topic_label,
            "topic_profile_id": topic_profile_id_value,
            "product_description": task.product_description,
        },
        "data_lineage": data_lineage,
        "aggregates": aggregates,
        "business_signals": {
            "high_value_pains": high_value_pains,
            "brand_pain": brand_pain,
            "solutions": solutions_block,
            "buying_opportunities": list(opportunities_payload),
            "competitor_insights": list(competitors_payload),
            "ps_ratio": round(ps_ratio_value, 2) if ps_ratio_value is not None else None,
        },
        "sample_posts_db": sample_posts_db,
        "sample_comments_db": sample_comments_db,
    }
    quality = quality_check_facts_v2(
        facts_v2_package,
        profile=topic_profile,
        # 即便没有 topic_profile，也尝试用 meta.product_description 里的英文 token 做兜底拦截；
        # 若没有任何可用 token，quality gate 内部会自动标记 topic_check_skipped。
        skip_topic_check=False,
    )
    report_tier = quality.tier
    facts_v2_quality = {
        "passed": bool(quality.passed),
        "tier": quality.tier,
        "flags": list(quality.flags),
        "metrics": dict(quality.metrics),
    }
    if analysis_blocked_reason == "insufficient_samples" and report_tier != "X_blocked":
        report_tier = "C_scouting"
        facts_v2_quality["tier"] = "C_scouting"
        facts_v2_quality["passed"] = True
        flags = set(str(x) for x in (facts_v2_quality.get("flags") or []))
        flags.add("insufficient_samples")
        facts_v2_quality["flags"] = sorted(flags)
        metrics = facts_v2_quality.get("metrics")
        if isinstance(metrics, dict):
            metrics.setdefault("filtered_posts", int(len(deduped_posts)))
            metrics.setdefault("min_required_posts", int(min_posts))
            metrics.setdefault("lookback_days", int(lookback_days))

    # 按门禁做“保守降级”：不改主流程，只控制输出强度
    if report_tier == "B_trimmed":
        insights["pain_points"] = list(insights.get("pain_points") or [])[:2]
        insights["opportunities"] = list(insights.get("opportunities") or [])[:2]
        insights["action_items"] = list(insights.get("action_items") or [])[:1]
        action_reports = list(insights.get("action_items") or [])
    elif report_tier in {"C_scouting", "X_blocked"}:
        insights = {
            "pain_points": [],
            "competitors": [],
            "opportunities": [],
            "action_items": [],
        }
        action_reports = []

    collection_warnings = _build_collection_warnings(
        stale_cache_subreddits,
        stale_cache_fallback_subreddits,
        api_failure_details,
    )
    trend_degraded, trend_sources = await _check_trend_views_freshness()
    coverage_tier = (
        facts_v2_quality.get("metrics", {}).get("coverage_tier")
        if isinstance(facts_v2_quality, dict)
        else None
    )
    if coverage_tier and coverage_tier != "full":
        trend_degraded = True
        if not trend_sources:
            trend_sources = []
        coverage_reason = f"coverage_{coverage_tier}"
        if coverage_reason not in trend_sources:
            trend_sources.append(coverage_reason)

    if report_tier not in {"C_scouting", "X_blocked"}:
        insights["trend_summary"] = summarize_trend_series(
            trend_series,
            degraded=bool(trend_degraded),
            sources=trend_sources or None,
        )

    facts_slice = None
    knowledge_graph: dict[str, Any] | None = None
    if facts_v2_package is not None:
        insights_map = insights if isinstance(insights, Mapping) else {}
        facts_slice = build_facts_slice_for_report(
            facts_v2_package=facts_v2_package,
            facts_v2_quality=facts_v2_quality if isinstance(facts_v2_quality, Mapping) else None,
            trend_summary=insights_map.get("trend_summary") if isinstance(insights_map, Mapping) else None,
            market_saturation=insights_map.get("market_saturation") if isinstance(insights_map, Mapping) else None,
            battlefield_profiles=insights_map.get("battlefield_profiles") if isinstance(insights_map, Mapping) else None,
            top_drivers=insights_map.get("top_drivers") if isinstance(insights_map, Mapping) else None,
        )
        if ps_ratio_value is not None:
            facts_slice["ps_ratio"] = round(ps_ratio_value, 2)
        knowledge_graph = _build_knowledge_graph(
            aggregates=aggregates,
            high_value_pains=high_value_pains,
            sample_posts_db=sample_posts_db,
            sample_comments_db=sample_comments_db,
            top_drivers=insights_map.get("top_drivers") if isinstance(insights_map, Mapping) else None,
        )
        facts_slice["knowledge_graph"] = knowledge_graph

    sources = {
        "communities": [entry.profile.name for entry in collected],
        "posts_analyzed": len(deduped_posts),
        "comments_analyzed": len(sample_comments_db),
        "data_lineage": data_lineage,
        "counts_analyzed": {
            "posts": len(deduped_posts),
            "comments": len(sample_comments_db),
        },
        "counts_db": {
            "posts_current": int(posts_db_current),
            "comments_total": int(comments_db_total),
            "comments_eligible": int(comments_db_eligible),
        },
        "comments_pipeline_status": comments_pipeline_status,
        "lookback_days": int(lookback_days),
        "cache_hit_rate": round(cache_hit_rate, 2),
        "ps_ratio": round(ps_ratio_value, 2) if ps_ratio_value is not None else None,
        "pain_counts_by_community": pain_counts_by_community,
        "keywords": list(keywords),
        "fetch_keywords": list(fetch_keywords),
        "analysis_duration_seconds": processing_seconds,
        "hybrid_posts_used": len(hybrid_posts),
        "reddit_api_calls": api_call_count,
        "reddit_api_failures": api_failure_details,
        "stale_cache_subreddits": sorted(stale_cache_subreddits),
        "stale_cache_fallback_subreddits": sorted(stale_cache_fallback_subreddits),
        "collection_warnings": collection_warnings,
        "product_description": task.product_description,
        "mode": getattr(task, "mode", "market_insight"),
        "audit_level": getattr(task, "audit_level", "lab"),
        "topic_profile_id": topic_profile_id if topic_profile is not None else None,
        "topic_profile": (
            {
                "id": topic_profile.id,
                "topic_name": topic_profile.topic_name,
                "vertical": topic_profile.vertical,
                "allowed_communities": list(topic_profile.allowed_communities or []),
                "community_patterns": list(topic_profile.community_patterns or []),
                "require_context_for_fetch": bool(topic_profile.require_context_for_fetch),
            }
            if topic_profile is not None
            else None
        ),
        "communities_detail": communities_detail,
        "duplicates_summary": duplicate_summary,
        "facts_v2_quality": facts_v2_quality,
        "report_tier": report_tier,
        "dedup_stats": {
            "total_posts": dedup_stats.total_posts,
            "candidate_pairs": dedup_stats.candidate_pairs,
            "fallback_pairs": dedup_stats.fallback_pairs,
            "similarity_checks": dedup_stats.similarity_checks,
        },
        "post_score_stats": post_score_stats,
        "noise_pool_stats": noise_pool_stats,
        "seed_source": seed_source,
        "data_source": data_source_label,
        "coverage_status": coverage_summary,
        "trend_degraded": trend_degraded,
        "trend_source": trend_sources or None,
    }
    if data_readiness is not None:
        sources["data_readiness"] = data_readiness
    if all_remediation_actions:
        sources["remediation_actions"] = all_remediation_actions
    if facts_v2_package is not None:
        # 用于审计/追溯：完整 facts_v2 包会在落库时另存到 facts_snapshots 表。
        sources["facts_v2_package"] = facts_v2_package
    if facts_slice is not None:
        sources["facts_slice"] = facts_slice
    if knowledge_graph is not None:
        sources["knowledge_graph"] = knowledge_graph
    if analysis_blocked_reason:
        sources["analysis_blocked"] = analysis_blocked_reason
    if report_tier == "X_blocked":
        sources.setdefault("analysis_blocked", "quality_gate_blocked")
    if report_tier == "C_scouting":
        sources.setdefault("analysis_blocked", "scouting_brief")

    # 将本次分析涉及的社区写入 discovered_communities，便于后续查询/回溯
    try:
        await _record_discovered_communities(task.id, collected, keywords)
    except Exception:
        logger.warning("Failed to record discovered communities", exc_info=True)

    flags: list[str] = []
    suggestion = ""
    if report_tier == "X_blocked":
        flags = (facts_v2_quality or {}).get("flags", []) if isinstance(facts_v2_quality, dict) else []
        if topic_profile_id_value:
            suggestion = "换一个更准的 `topic_profile_id`，或扩充样本（更多社区/更长时间窗/更明确关键词）。"
        else:
            suggestion = "先扩充样本（更多社区/更长时间窗/更明确关键词），再看是否需要建立 topic_profile。"
    if report_tier == "X_blocked":
        report_html = dedent(
            f"""
            [Reddit Signal Scanner] 报告拦截（X_blocked）

            这次数据不够“下结论”，所以系统把报告拦住了，避免输出误导性结论。

            - 原因：{", ".join([str(x) for x in flags]) or "unknown"}
            - 建议：{suggestion}
            """
        ).strip()
    elif report_tier == "C_scouting":
        report_html = _render_scouting_report(task, collected, sources)
    else:
        report_html = _render_report(task, collected, insights, sources)

    structured_report = None
    try:
        structured_report = await _render_structured_report_with_llm(
            task=task,
            facts_slice=facts_slice,
            report_tier=report_tier,
            settings=settings,
        )
    except Exception:
        structured_report = None
    if structured_report:
        sources["report_structured"] = structured_report
    sources["llm_used"] = bool(structured_report)
    sources["llm_model"] = settings.llm_model_name if structured_report else None
    sources["llm_rounds"] = 1 if structured_report else 0

    # 计算置信度分数 (0.0-1.0)
    # 从 sources 和 insights 中提取数据（使用类型断言）
    cache_hit_rate_value = sources["cache_hit_rate"]
    posts_analyzed_value = sources["posts_analyzed"]
    communities_value = sources["communities"]
    pain_points_value = insights["pain_points"]
    competitors_value = insights["competitors"]
    opportunities_value = insights["opportunities"]

    confidence_score = _calculate_confidence_score(
        cache_hit_rate=float(cache_hit_rate_value)
        if isinstance(cache_hit_rate_value, (int, float))
        else 0.0,
        posts_analyzed=int(posts_analyzed_value)
        if isinstance(posts_analyzed_value, int)
        else 0,
        communities_found=len(communities_value)
        if isinstance(communities_value, list)
        else 0,
        pain_points_count=len(pain_points_value)
        if isinstance(pain_points_value, list)
        else 0,
        competitors_count=len(competitors_value)
        if isinstance(competitors_value, list)
        else 0,
        opportunities_count=len(opportunities_value)
        if isinstance(opportunities_value, list)
        else 0,
    )

    # 关闭临时创建的服务（如果有）
    if close_reddit and service is not None:
        if hasattr(service, "close"):
            await service.close()
        elif hasattr(service, "reddit") and hasattr(service.reddit, "close"):
            await service.reddit.close()

    return AnalysisResult(
        insights=insights,
        sources=sources,
        report_html=report_html,
        action_items=action_reports,
        confidence_score=confidence_score,
    )


def _build_data_collection_service(settings: Settings) -> DataCollectionService | None:
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


def _collection_from_result(
    profiles: Sequence[CommunityProfile],
    result: CollectionResult,
) -> tuple[List[CollectedCommunity], int, int, int]:
    collected: List[CollectedCommunity] = []
    total_cache_hits = 0
    total_cache_misses = 0
    total_posts = 0
    for profile in profiles:
        # DataCollectionService 会把社区名统一成 r/<lowercase>，这里也按同一口径取数，
        # 否则像 "r/PPC" 这种大小写混用会导致“明明有数据却当成空”。
        canonical_name = _normalise_community_name(profile.name)
        posts = result.posts_by_subreddit.get(canonical_name)
        if posts is None:
            posts = result.posts_by_subreddit.get(profile.name, [])
        payload = []
        for post in posts:
            normalised = _reddit_post_to_dict(post)
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


async def _try_cache_only_collection(
    profiles: Sequence[CommunityProfile],
    settings: Settings,
    cache_manager: CacheManager | None = None,
) -> CollectionResult | None:
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


def _reddit_post_to_dict(post: Any) -> Dict[str, Any]:
    """
    Normalize various post payload shapes to a flat dict understood by downstream steps.

    Defensive cases:
    - cached payload可能是 list[RedditPost] 或嵌套 list[dict]，取第一个有效元素
    - dict 形式的帖子（缺少属性访问）也要兼容
    - 非法/空对象直接返回 {}
    """
    if post is None:
        return {}

    # 1. 处理 List/Tuple (递归解包)
    if isinstance(post, (list, tuple)):
        for item in post:
            normalised = _reddit_post_to_dict(item)
            if normalised:
                return normalised
        return {}

    # 2. 处理 Dict (直接取值)
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

    # 3. 处理 Object (RedditPost)
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
        # 兜底：如果对象既不是 dict 也不是 list，但也没有预期的属性，
        # 可能是某种 Proxy 对象或仅部分实现的 Mock 对象。
        # 记录日志并返回空，避免阻断整个流程。
        return {}
    except Exception:
        return {}


__all__ = ["AnalysisResult", "run_analysis", "InsufficientDataError"]
