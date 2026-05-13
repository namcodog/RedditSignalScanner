from __future__ import annotations

import json
import logging
from typing import Optional, Any, Dict, List, Mapping, Sequence

from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.analysis.signal_extraction import (
    BusinessSignals,
    CompetitorSignal,
    OpportunitySignal,
    PainPointSignal,
    SolutionSignal,
)
from app.services.semantic.embedding_service import MODEL_NAME

logger = logging.getLogger(__name__)
_MIN_LABEL_SOLUTIONS = 4
_MIN_LABEL_OPPORTUNITIES = 2


def normalize_target_ids(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if value:
            out.append(value)
    return out


def looks_like_reddit_post_id(raw: str) -> bool:
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


def truncate_target_ids(
    target_ids: list[str],
    *,
    max_items: int,
) -> tuple[list[str], int, bool]:
    cleaned = [str(x or "").strip() for x in (target_ids or []) if str(x or "").strip()]
    total = len(cleaned)
    if max_items <= 0:
        return [], total, total > 0
    if total <= max_items:
        return cleaned, total, False
    return cleaned[:max_items], total, True


def build_data_lineage(
    *,
    source_range:Optional[ dict[str, int]] = None,
    coverage:Optional[ dict[str, Any]] = None,
    remediation_actions:Optional[ Sequence[Mapping[str, Any]]] = None,
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

        ids = normalize_target_ids(action.get("target_ids"))
        for target_id in ids:
            if target_id not in target_ids:
                target_ids.append(target_id)

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


def merge_posts_by_id(
    primary: list[dict[str, Any]],
    extra: Sequence[dict[str, Any]],
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


def parse_embedding_value(value: Any) ->Optional[ list[float]]:
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


async def fetch_post_embeddings(
    session: Any,
    posts: Sequence[Dict[str, Any]],
    *,
    model_name: str = MODEL_NAME,
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
        {"ids": ids, "model_version": model_name},
    )
    out: dict[str, list[float]] = {}
    for row in rows.mappings().all():
        post_id = row.get("post_id")
        embedding = parse_embedding_value(row.get("embedding"))
        if post_id is None or embedding is None:
            continue
        out[str(post_id)] = embedding
    return out


async def extract_business_signals_from_labels(
    post_ids: Sequence[int],
    *,
    session_factory: Any = SessionFactory,
) ->Optional[ BusinessSignals]:
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
        async with session_factory() as session:
            label_rows = await session.execute(
                text(
                    """
                    SELECT
                        so.label_key AS category,
                        so.label_value AS aspect,
                        COUNT(*) as count,
                        AVG(so.confidence) as avg_sentiment,
                        jsonb_agg(DISTINCT c.post_id) as sample_post_ids
                    FROM semantic_observation so
                    JOIN comments c
                      ON so.content_type = 'comment'
                     AND so.content_id = c.id
                    WHERE c.post_id = ANY(:post_ids)
                      AND so.observation_type = 'content_label'
                    GROUP BY so.label_key, so.label_value
                    """
                ),
                {"post_ids": numeric_post_ids},
            )
            labels = label_rows.mappings().all()

            entity_rows = await session.execute(
                text(
                    """
                    SELECT
                        so.label_value AS entity_name,
                        COUNT(*) as mentions,
                        jsonb_agg(DISTINCT c.post_id) as sample_post_ids
                    FROM semantic_observation so
                    JOIN comments c
                      ON so.content_type = 'comment'
                     AND so.content_id = c.id
                    WHERE c.post_id = ANY(:post_ids)
                      AND so.observation_type = 'content_entity'
                      AND so.label_key = 'brand'
                    GROUP BY so.label_value
                    """
                ),
                {"post_ids": numeric_post_ids},
            )
            entities = entity_rows.mappings().all()
    except Exception as exc:  # pragma: no cover
        logger.warning("Label-based signal extraction failed, fallback to heuristics: %s", exc)
        return None

    if not labels and not entities:
        return None

    pain_total = 0
    solution_total = 0
    intent_total = 0
    pain_signals: list[PainPointSignal] = []
    opportunity_signals: list[OpportunitySignal] = []
    solution_signals: list[SolutionSignal] = []
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
            solution_signals.append(
                SolutionSignal(
                    description=f"{aspect} 解决方案",
                    frequency=max(1, count),
                    sentiment=max(0.0, avg_sentiment),
                    source_posts=sample_posts,
                    relevance=0.85,
                )
            )
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
    ps_ratio = pain_total / denominator if denominator > 0 else (float(pain_total) if pain_total < 10 else 10.0)

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
        solutions=solution_signals,
        ps_ratio=ps_ratio,
    )


def merge_business_signals_with_heuristics(
    primary: BusinessSignals,
    heuristic: BusinessSignals,
) -> BusinessSignals:
    merged_opportunities = list(primary.opportunities)
    if len(merged_opportunities) < _MIN_LABEL_OPPORTUNITIES:
        seen = {str(item.description or "").strip().casefold() for item in merged_opportunities}
        for item in heuristic.opportunities:
            key = str(item.description or "").strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged_opportunities.append(item)

    merged_solutions = list(primary.solutions)
    if len(merged_solutions) < _MIN_LABEL_SOLUTIONS:
        seen = {str(item.description or "").strip().casefold() for item in merged_solutions}
        for item in heuristic.solutions:
            key = str(item.description or "").strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged_solutions.append(item)

    return BusinessSignals(
        pain_points=list(primary.pain_points),
        competitors=list(primary.competitors),
        opportunities=merged_opportunities,
        solutions=merged_solutions,
        ps_ratio=primary.ps_ratio if primary.ps_ratio is not None else heuristic.ps_ratio,
    )
