from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from textwrap import dedent
from typing import Optional, Any, Awaitable, Callable, Mapping, Sequence

from sqlalchemy import text
from app.schemas.task import TaskSummary
from app.services.analysis import sample_guard
from app.services.analysis.topic_profiles import TopicProfile, normalize_subreddit


@dataclass(slots=True)
class InsufficientSampleArtifacts:
    insights: dict[str, Any]
    sources: dict[str, Any]
    report_html: str
    action_items: list[dict[str, Any]]
    confidence_score: float


def _normalize_target_communities(allowed: Sequence[str]) -> tuple[list[str], list[str]]:
    target_communities: list[str] = []
    target_keys: list[str] = []
    for raw in allowed:
        normalized = normalize_subreddit(str(raw or ""))
        if not normalized:
            continue
        key = normalized.removeprefix("r/").strip().lower()
        if not key:
            continue
        target_communities.append(normalized)
        target_keys.append(key)
    return target_communities, target_keys


def _derive_truth_status(row: Mapping[str, Any]) -> str:
    if not bool(row.get("registry_enabled")):
        return "DISABLED"
    if not bool(row.get("has_membership")):
        return "MISSING_MEMBERSHIP"
    if not bool(row.get("is_approved")):
        return "UNAPPROVED"
    if not bool(row.get("has_runtime")):
        return "MISSING_RUNTIME"
    notes = row.get("runtime_notes") or {}
    if isinstance(notes, Mapping):
        raw = str(notes.get("backfill_status") or "").strip().upper()
        if raw:
            return raw
    crawl_status = str(row.get("crawl_status") or "").strip().lower()
    if crawl_status == "needs_backfill":
        return "NEEDS"
    if crawl_status == "paused":
        return "PAUSED"
    if crawl_status == "blocked":
        return "BLOCKED"
    if crawl_status == "active":
        return "ACTIVE_UNKNOWN"
    return "UNKNOWN"


def _compute_coverage_months(backfill_floor: Any) -> int:
    if not isinstance(backfill_floor, datetime):
        return 0
    now = datetime.now(timezone.utc)
    anchor = backfill_floor.astimezone(timezone.utc)
    return max(0, (now - anchor).days // 30)


async def run_sample_guard_check(
    *,
    keywords: Sequence[str],
    product_description: str,
    lookback_days: int,
    min_sample_size: int,
    hot_fetcher: Callable[...Optional[, Awaitable[list[dict[str, object]]]]],
    cold_fetcher: Callable[...Optional[, Awaitable[list[dict[str, object]]]]],
    supplementer: Callable[...Optional[, Awaitable[list[dict[str, object]]]]],
) -> sample_guard.Optional[SampleCheckResult]:
    if not keywords and not product_description.strip():
        return None
    try:
        return await sample_guard.check_sample_size(
            hot_fetcher=hot_fetcher,
            cold_fetcher=cold_fetcher,
            supplementer=supplementer,
            keywords=keywords,
            min_samples=min_sample_size,
            lookback_days=lookback_days,
        )
    except Exception:
        return None


async def build_data_readiness_snapshot(
    *,
    topic_profile: TopicProfile,
    session_factory: Callable[[], Any],
) -> dict[str, Any]:
    target_communities, target_keys = _normalize_target_communities(
        topic_profile.allowed_communities or []
    )

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

    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                WITH current_membership AS (
                    SELECT DISTINCT community_id
                    FROM community_domain_membership
                    WHERE is_current = TRUE
                ),
                approved_membership AS (
                    SELECT DISTINCT m.community_id
                    FROM community_domain_membership m
                    JOIN community_governance_decision g
                      ON g.membership_id = m.id
                    WHERE m.is_current = TRUE
                      AND g.is_current = TRUE
                      AND g.decision = 'approved'
                )
                SELECT
                    lower(regexp_replace(r.community_name, '^r/', '', 'i')) AS community_key,
                    r.community_name,
                    r.is_enabled AS registry_enabled,
                    (cm.community_id IS NOT NULL) AS has_membership,
                    (am.community_id IS NOT NULL) AS is_approved,
                    (s.community_id IS NOT NULL) AS has_runtime,
                    s.crawl_status,
                    s.sample_posts,
                    s.sample_comments,
                    s.last_crawled_at,
                    s.backfill_floor,
                    s.runtime_notes
                FROM community_registry r
                LEFT JOIN current_membership cm
                  ON cm.community_id = r.id
                LEFT JOIN approved_membership am
                  ON am.community_id = r.id
                LEFT JOIN community_runtime_state s
                  ON s.community_id = r.id
                WHERE r.platform = 'reddit'
                  AND lower(regexp_replace(r.community_name, '^r/', '', 'i'))
                      = ANY(CAST(:target_keys AS text[]))
                """
            ),
            {"target_keys": target_keys},
        )
        rows = list(result.mappings().all())

    by_key: dict[str, Mapping[str, Any]] = {
        str(row["community_key"] or ""): row for row in rows if row.get("community_key")
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

        status = _derive_truth_status(row)
        status_counts[status] += 1
        cm = _compute_coverage_months(row.get("backfill_floor"))
        coverage_months.append(cm)
        sp = int(row.get("sample_posts") or 0)
        sc = int(row.get("sample_comments") or 0)
        sample_posts_total += sp
        sample_comments_total += sc

        last_crawled = row.get("last_crawled_at")
        details.append(
            {
                "community": str(row.get("community_name") or expected),
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
        "communities_found": len(by_key),
        "missing_communities": missing,
        "status_counts": dict(status_counts),
        "sample_posts_total": int(sample_posts_total),
        "sample_comments_total": int(sample_comments_total),
        "coverage_months_min": int(cm_min),
        "coverage_months_avg": float(cm_avg),
        "coverage_months_max": int(cm_max),
        "communities": details,
    }


def build_insufficient_sample_artifacts(
    *,
    task: TaskSummary,
    sample_result: sample_guard.SampleCheckResult,
    lookback_days: int,
    min_sample_size: int,
) -> InsufficientSampleArtifacts:
    status_payload = {
        "hot_count": sample_result.hot_count,
        "cold_count": sample_result.cold_count,
        "combined_count": sample_result.combined_count,
        "shortfall": sample_result.shortfall,
        "remaining_shortfall": sample_result.remaining_shortfall,
        "supplemented": sample_result.supplemented,
        "supplement_posts": sample_result.supplement_posts,
        "min_required": min_sample_size,
        "lookback_days": max(1, int(lookback_days)),
    }
    report_html = dedent(
        f"""
        <html>
          <body>
            <h1>分析暂停：样本不足</h1>
            <p>当前缓存+冷库共收集 <strong>{sample_result.combined_count}</strong> 条帖子，未达到启动分析所需的 {min_sample_size} 条。</p>
            <p>已触发补抓流程，请稍后重新尝试。若需立即分析，可扩大关键词或延长时间范围。</p>
          </body>
        </html>
        """
    ).strip()
    sources: dict[str, Any] = {
        "communities": [],
        "posts_analyzed": int(sample_result.combined_count),
        "comments_analyzed": 0,
        "counts_analyzed": {
            "posts": int(sample_result.combined_count),
            "comments": 0,
        },
        "counts_db": {
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
        "structured_llm_status": "skipped",
        "structured_llm_reason": "insufficient_samples",
        "llm_used": False,
        "llm_model": None,
        "llm_rounds": 0,
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
    return InsufficientSampleArtifacts(
        insights={"pain_points": [], "competitors": [], "opportunities": []},
        sources=sources,
        report_html=report_html,
        action_items=[],
        confidence_score=0.0,
    )
