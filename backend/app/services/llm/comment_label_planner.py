from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from sqlalchemy import text as sqltext

from app.db.session import SessionFactory
from app.services.llm.label_prefilter import (
    DOMAIN_ORDER,
    CommentPrefilterStats,
    allocate_domain_quotas,
    build_batch_plan,
    prefilter_comment_rows,
    select_activation_rows,
)

HIGH_SCORE_MIN = 9.0
LOW_SCORE_MAX = 2.0
HIGH_SCORE_RATIO = 0.3
MIN_COMMENT_CHARS = 20


@dataclass(slots=True)
class IncrementalCommentLabelPlan:
    candidates: list[dict[str, Any]]
    prefilter_stats: CommentPrefilterStats
    raw_candidate_count: int


@dataclass(slots=True)
class CommentActivationBatch:
    batch: int
    items: list[dict[str, Any]]

    @property
    def size(self) -> int:
        return len(self.items)


@dataclass(slots=True)
class HistoricalCommentActivationPlan:
    batches: list[CommentActivationBatch]
    summary: dict[str, Any]

    def payload_batches(self) -> list[list[dict[str, Any]]]:
        return [batch.items for batch in self.batches]


def _split_limits(limit: int, high_ratio: float) -> tuple[int, int]:
    if limit <= 0:
        return 0, 0
    high_limit = int(round(limit * high_ratio))
    high_limit = min(limit, max(0, high_limit))
    mid_limit = max(0, limit - high_limit)
    return mid_limit, high_limit


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


def interleave_selected_rows_by_domain(
    rows_by_domain: Mapping[str, Sequence[dict[str, Any]]],
) -> list[dict[str, Any]]:
    queues = {
        domain: deque(items)
        for domain, items in rows_by_domain.items()
        if items
    }
    ordered: list[dict[str, Any]] = []
    while queues:
        for domain in DOMAIN_ORDER:
            queue = queues.get(domain)
            if queue is None:
                continue
            if queue:
                ordered.append(queue.popleft())
            if not queue:
                queues.pop(domain, None)
    return ordered


def _comment_payload_from_row(
    row: Mapping[str, Any], *, max_body_chars: int
) -> dict[str, Any]:
    return {
        "task_type": "comment_label",
        "id": int(row.get("id")),
        "subreddit": str(row.get("subreddit") or ""),
        "post_title": _truncate(str(row.get("post_title") or ""), max_body_chars),
        "comment_body": _truncate(str(row.get("body") or ""), max_body_chars),
        "domain": str(row.get("domain") or ""),
        "business_pool": str(row.get("business_pool") or "unscored"),
    }


def build_incremental_comment_label_plan_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    min_chars: int = MIN_COMMENT_CHARS,
) -> IncrementalCommentLabelPlan:
    candidates, prefilter_stats = prefilter_comment_rows(
        rows,
        min_chars=min_chars,
        allowed_pools={"core", "lab"},
    )
    return IncrementalCommentLabelPlan(
        candidates=candidates,
        prefilter_stats=prefilter_stats,
        raw_candidate_count=len(rows),
    )


async def _fetch_incremental_comment_candidate_rows(
    limit: int,
    lookback_days: int,
) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        mid_limit, high_limit = _split_limits(limit, HIGH_SCORE_RATIO)
        rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        base_params = {"days": int(lookback_days)}

        if mid_limit > 0:
            result = await session.execute(
                sqltext(
                    """
                    SELECT c.id,
                           c.body,
                           c.subreddit,
                           c.score,
                           c.source,
                           c.source_post_id,
                           c.created_utc,
                           p.title AS post_title,
                           cs.value_score,
                           cs.business_pool
                    FROM comments c
                    JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    JOIN posts_raw p
                      ON p.source = c.source
                     AND p.source_post_id = c.source_post_id
                     AND p.is_current = TRUE
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cs.business_pool IN ('core','lab')
                      AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.comment_id IS NULL
                      AND cs.value_score > :low_score
                      AND cs.value_score < :high_score
                    ORDER BY cs.value_score DESC, c.score DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(mid_limit),
                    "low_score": LOW_SCORE_MAX,
                    "high_score": HIGH_SCORE_MIN,
                },
            )
            for row in result.mappings().all():
                comment_id = int(row["id"])
                if comment_id in seen:
                    continue
                seen.add(comment_id)
                rows.append(dict(row))

        if high_limit > 0:
            result = await session.execute(
                sqltext(
                    """
                    SELECT c.id,
                           c.body,
                           c.subreddit,
                           c.score,
                           c.source,
                           c.source_post_id,
                           c.created_utc,
                           p.title AS post_title,
                           cs.value_score,
                           cs.business_pool
                    FROM comments c
                    JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    JOIN posts_raw p
                      ON p.source = c.source
                     AND p.source_post_id = c.source_post_id
                     AND p.is_current = TRUE
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cs.business_pool IN ('core','lab')
                      AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.comment_id IS NULL
                      AND cs.value_score >= :high_score
                    ORDER BY cs.value_score DESC, c.score DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(high_limit),
                    "high_score": HIGH_SCORE_MIN,
                },
            )
            for row in result.mappings().all():
                comment_id = int(row["id"])
                if comment_id in seen:
                    continue
                seen.add(comment_id)
                rows.append(dict(row))

        return rows


async def build_incremental_comment_label_plan(
    limit: int,
    lookback_days: int,
) -> IncrementalCommentLabelPlan:
    rows = await _fetch_incremental_comment_candidate_rows(limit, lookback_days)
    return build_incremental_comment_label_plan_from_rows(rows)


def _build_comment_activation_batches(
    *,
    selected_rows: list[dict[str, Any]],
    max_body_chars: int,
    quotas: dict[str, int],
    distribution: dict[str, int],
    batch_sizes: list[int],
    prefilter_stats: dict[str, int],
) -> HistoricalCommentActivationPlan:
    payload = [
        _comment_payload_from_row(row, max_body_chars=max_body_chars)
        for row in selected_rows
    ]

    batches: list[CommentActivationBatch] = []
    cursor = 0
    for idx, current_size in enumerate(batch_sizes, start=1):
        items = payload[cursor : cursor + current_size]
        batches.append(CommentActivationBatch(batch=idx, items=items))
        cursor += current_size

    pool_distribution = {"core": 0, "lab": 0, "unscored": 0}
    for row in selected_rows:
        pool = str(row.get("business_pool") or "unscored").lower()
        pool_distribution[pool if pool in pool_distribution else "unscored"] += 1

    summary = {
        "eligible_comment_pool": sum(distribution.values()),
        "activation_backlog": len(payload),
        "rule_stats": prefilter_stats,
        "domain_distribution": {
            domain: int(distribution.get(domain, 0))
            for domain in DOMAIN_ORDER
            if distribution.get(domain, 0)
        },
        "domain_quotas": {
            domain: int(quotas.get(domain, 0))
            for domain in DOMAIN_ORDER
            if quotas.get(domain, 0)
        },
        "pool_distribution": pool_distribution,
        "batch_plan": [
            {"batch": batch.batch, "size": batch.size}
            for batch in batches
        ],
    }
    return HistoricalCommentActivationPlan(batches=batches, summary=summary)


def build_comment_activation_export_plan(
    *,
    rows: Sequence[Mapping[str, Any]],
    max_body_chars: int,
    effective_domain_weights: Mapping[str, int],
    target_total: int,
    base_quota: int,
    first_batch_size: int,
    batch_size: int,
) -> HistoricalCommentActivationPlan:
    filtered_rows, prefilter_stats = prefilter_comment_rows(
        rows,
        min_chars=MIN_COMMENT_CHARS,
    )
    selected_rows, quotas, distribution = select_activation_rows(
        filtered_rows,
        weight_counts=effective_domain_weights,
        target_total=target_total,
        base_quota=base_quota,
    )
    batch_sizes = build_batch_plan(
        len(selected_rows),
        first_batch_size=first_batch_size,
        batch_size=batch_size,
    )
    return _build_comment_activation_batches(
        selected_rows=selected_rows,
        max_body_chars=max_body_chars,
        quotas=quotas,
        distribution=distribution,
        batch_sizes=batch_sizes,
        prefilter_stats=prefilter_stats.to_dict(),
    )


async def _count_raw_unlabeled_comments(*, cutoff_utc: datetime | None = None) -> int:
    async with SessionFactory() as session:
        where_clause = "WHERE llm.comment_id IS NULL"
        params: dict[str, Any] = {}
        if cutoff_utc is not None:
            where_clause += " AND c.created_utc >= :cutoff_utc"
            params["cutoff_utc"] = cutoff_utc
        result = await session.execute(
            sqltext(
                f"""
                SELECT COUNT(*)
                FROM comments c
                LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                {where_clause}
                """
            ),
            params,
        )
        return int(result.scalar_one())


async def _fetch_effective_domain_weights() -> dict[str, int]:
    async with SessionFactory() as session:
        result = await session.execute(
            sqltext(
                """
                SELECT category, COUNT(*) AS effective_communities
                FROM (
                    SELECT jsonb_array_elements_text(cp.categories) AS category
                    FROM community_pool cp
                    WHERE cp.is_active = TRUE
                      AND cp.deleted_at IS NULL
                      AND cp.is_blacklisted = FALSE
                      AND jsonb_typeof(cp.categories) = 'array'
                      AND jsonb_array_length(cp.categories) > 0
                ) t
                GROUP BY category
                """
            )
        )
        return {
            str(row._mapping["category"]): int(row._mapping["effective_communities"])
            for row in result.fetchall()
        }


async def _fetch_activation_candidate_counts(
    *,
    lookback_days: int,
) -> tuple[dict[str, int], dict[str, int]]:
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=int(lookback_days))
    async with SessionFactory() as session:
        result = await session.execute(
            sqltext(
                """
                SELECT category, COUNT(*) AS n
                FROM (
                    SELECT DISTINCT c.id, cat.category
                    FROM comments c
                    JOIN community_pool cp
                      ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                    CROSS JOIN LATERAL jsonb_array_elements_text(cp.categories) AS cat(category)
                    LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cp.is_active = TRUE
                      AND cp.deleted_at IS NULL
                      AND cp.is_blacklisted = FALSE
                      AND llm.comment_id IS NULL
                      AND c.created_utc >= :cutoff_utc
                      AND length(trim(coalesce(c.body, ''))) >= :min_chars
                      AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                ) t
                GROUP BY category
                """
            ),
            {"cutoff_utc": cutoff_utc, "min_chars": MIN_COMMENT_CHARS},
        )
        candidate_counts = {
            str(row._mapping["category"]): int(row._mapping["n"])
            for row in result.fetchall()
        }

        pool_result = await session.execute(
            sqltext(
                """
                SELECT COALESCE(cs.business_pool, 'unscored') AS pool, COUNT(*) AS n
                FROM comments c
                JOIN community_pool cp
                  ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                WHERE cp.is_active = TRUE
                  AND cp.deleted_at IS NULL
                  AND cp.is_blacklisted = FALSE
                  AND llm.comment_id IS NULL
                  AND c.created_utc >= :cutoff_utc
                  AND length(trim(coalesce(c.body, ''))) >= :min_chars
                  AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                GROUP BY COALESCE(cs.business_pool, 'unscored')
                """
            ),
            {"cutoff_utc": cutoff_utc, "min_chars": MIN_COMMENT_CHARS},
        )
        pool_counts = {
            str(row._mapping["pool"]): int(row._mapping["n"])
            for row in pool_result.fetchall()
        }
        return candidate_counts, pool_counts


async def _fetch_activation_prefilter_stats(*, lookback_days: int) -> dict[str, int]:
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=int(lookback_days))
    async with SessionFactory() as session:
        total_effective = await session.scalar(
            sqltext(
                """
                SELECT COUNT(*)
                FROM comments c
                JOIN community_pool cp
                  ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                WHERE cp.is_active = TRUE
                  AND cp.deleted_at IS NULL
                  AND cp.is_blacklisted = FALSE
                  AND llm.comment_id IS NULL
                  AND c.created_utc >= :cutoff_utc
                  AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                """
            ),
            {"cutoff_utc": cutoff_utc},
        )
        eligible_count = await session.scalar(
            sqltext(
                """
                SELECT COUNT(*)
                FROM comments c
                JOIN community_pool cp
                  ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                WHERE cp.is_active = TRUE
                  AND cp.deleted_at IS NULL
                  AND cp.is_blacklisted = FALSE
                  AND llm.comment_id IS NULL
                  AND c.created_utc >= :cutoff_utc
                  AND length(trim(coalesce(c.body, ''))) >= :min_chars
                  AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                """
            ),
            {"cutoff_utc": cutoff_utc, "min_chars": MIN_COMMENT_CHARS},
        )
        unique_after_rules = await session.scalar(
            sqltext(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT DISTINCT md5(lower(regexp_replace(trim(coalesce(c.body, '')), '\s+', ' ', 'g')))
                    FROM comments c
                    JOIN community_pool cp
                      ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                    LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cp.is_active = TRUE
                      AND cp.deleted_at IS NULL
                      AND cp.is_blacklisted = FALSE
                      AND llm.comment_id IS NULL
                      AND c.created_utc >= :cutoff_utc
                      AND length(trim(coalesce(c.body, ''))) >= :min_chars
                      AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                ) t
                """
            ),
            {"cutoff_utc": cutoff_utc, "min_chars": MIN_COMMENT_CHARS},
        )
        total_effective_int = int(total_effective or 0)
        eligible_count_int = int(eligible_count or 0)
        unique_after_rules_int = int(unique_after_rules or 0)
        return {
            "total_effective_unlabeled": total_effective_int,
            "filtered_short": max(0, total_effective_int - eligible_count_int),
            "deduped": max(0, eligible_count_int - unique_after_rules_int),
            "admitted": unique_after_rules_int,
        }


async def _fetch_domain_activation_candidates(
    *,
    domain: str,
    limit: int,
    lookback_days: int,
) -> list[dict[str, Any]]:
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=int(lookback_days))
    async with SessionFactory() as session:
        result = await session.execute(
            sqltext(
                """
                WITH ranked AS (
                    SELECT c.id,
                           c.body,
                           c.subreddit,
                           c.score,
                           c.source,
                           c.source_post_id,
                           c.created_utc,
                           p.title AS post_title,
                           p.score AS post_score,
                           p.num_comments AS post_num_comments,
                           cs.value_score,
                           COALESCE(cs.business_pool, 'unscored') AS business_pool,
                           cp.categories,
                           md5(lower(regexp_replace(trim(coalesce(c.body, '')), '\s+', ' ', 'g'))) AS body_hash,
                           ROW_NUMBER() OVER (
                               PARTITION BY md5(lower(regexp_replace(trim(coalesce(c.body, '')), '\s+', ' ', 'g')))
                               ORDER BY
                                 CASE COALESCE(cs.business_pool, 'unscored')
                                     WHEN 'core' THEN 2
                                     WHEN 'lab' THEN 1
                                     ELSE 0
                                 END DESC,
                                 COALESCE(cs.value_score, 0) DESC,
                                 c.score DESC,
                                 COALESCE(p.score, 0) DESC,
                                 COALESCE(p.num_comments, 0) DESC,
                                 length(trim(coalesce(c.body, ''))) DESC,
                                 c.id
                           ) AS dedup_rank
                    FROM comments c
                    JOIN community_pool cp
                      ON cp.name_key = regexp_replace(lower(coalesce(c.subreddit, '')), '^r/', '')
                    CROSS JOIN LATERAL jsonb_array_elements_text(cp.categories) AS cat(category)
                    LEFT JOIN posts_raw p
                      ON p.source = c.source
                     AND p.source_post_id = c.source_post_id
                     AND p.is_current = TRUE
                    LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cp.is_active = TRUE
                      AND cp.deleted_at IS NULL
                      AND cp.is_blacklisted = FALSE
                      AND llm.comment_id IS NULL
                      AND cat.category = :domain
                      AND c.created_utc >= :cutoff_utc
                      AND length(trim(coalesce(c.body, ''))) >= :min_chars
                      AND (cs.business_pool IS NULL OR cs.business_pool <> 'noise')
                )
                SELECT id,
                       body,
                       subreddit,
                       score,
                       source,
                       source_post_id,
                       created_utc,
                       post_title,
                       post_score,
                       post_num_comments,
                       value_score,
                       business_pool,
                       categories
                FROM ranked
                WHERE dedup_rank = 1
                ORDER BY
                    CASE business_pool
                        WHEN 'core' THEN 2
                        WHEN 'lab' THEN 1
                        ELSE 0
                    END DESC,
                    COALESCE(value_score, 0) DESC,
                    score DESC,
                    COALESCE(post_score, 0) DESC,
                    COALESCE(post_num_comments, 0) DESC,
                    length(trim(coalesce(body, ''))) DESC,
                    id
                LIMIT :limit
                """
            ),
            {
                "domain": domain,
                "cutoff_utc": cutoff_utc,
                "min_chars": MIN_COMMENT_CHARS,
                "limit": int(limit),
            },
        )
        rows = [dict(row) for row in result.mappings().all()]
        for row in rows:
            row["domain"] = domain
        return rows


async def build_historical_comment_activation_plan(
    *,
    lookback_days: int,
    max_body_chars: int,
    target_total: int,
    base_quota: int,
    first_batch_size: int,
    batch_size: int,
) -> HistoricalCommentActivationPlan:
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=int(lookback_days))
    raw_unlabeled_overall = await _count_raw_unlabeled_comments()
    raw_unlabeled_window = await _count_raw_unlabeled_comments(cutoff_utc=cutoff_utc)
    effective_weights = await _fetch_effective_domain_weights()
    candidate_counts, pool_counts = await _fetch_activation_candidate_counts(
        lookback_days=lookback_days
    )
    prefilter_stats = await _fetch_activation_prefilter_stats(
        lookback_days=lookback_days
    )

    quotas = allocate_domain_quotas(
        candidate_counts=candidate_counts,
        weight_counts=effective_weights,
        target_total=target_total,
        base_quota=base_quota,
    )
    selected_rows_by_domain: dict[str, list[dict[str, Any]]] = {}
    distribution: dict[str, int] = {}
    for domain in DOMAIN_ORDER:
        quota = int(quotas.get(domain, 0))
        if quota <= 0:
            continue
        rows = await _fetch_domain_activation_candidates(
            domain=domain,
            limit=quota,
            lookback_days=lookback_days,
        )
        if not rows:
            continue
        distribution[domain] = len(rows)
        selected_rows_by_domain[domain] = rows

    selected_rows = interleave_selected_rows_by_domain(selected_rows_by_domain)

    batch_sizes = build_batch_plan(
        len(selected_rows),
        first_batch_size=first_batch_size,
        batch_size=batch_size,
    )
    plan = _build_comment_activation_batches(
        selected_rows=selected_rows,
        max_body_chars=max_body_chars,
        quotas=quotas,
        distribution=distribution,
        batch_sizes=batch_sizes,
        prefilter_stats={
            "admitted": int(prefilter_stats.get("admitted", 0)),
            "filtered_short": int(prefilter_stats.get("filtered_short", 0)),
            "deduped": int(prefilter_stats.get("deduped", 0)),
            "skipped_pool": 0,
            "skipped_age": 0,
        },
    )
    plan.summary["eligible_comment_pool"] = int(prefilter_stats.get("admitted", 0))
    plan.summary["pool_distribution_raw"] = {
        "core": int(pool_counts.get("core", 0)),
        "lab": int(pool_counts.get("lab", 0)),
        "unscored": int(pool_counts.get("unscored", 0)),
    }
    plan.summary["raw_unlabeled_comments"] = int(raw_unlabeled_overall)
    plan.summary["raw_unlabeled_comments_window"] = int(raw_unlabeled_window)
    return plan


__all__ = [
    "CommentActivationBatch",
    "HIGH_SCORE_MIN",
    "HistoricalCommentActivationPlan",
    "HIGH_SCORE_RATIO",
    "IncrementalCommentLabelPlan",
    "LOW_SCORE_MAX",
    "MIN_COMMENT_CHARS",
    "build_comment_activation_export_plan",
    "build_historical_comment_activation_plan",
    "build_incremental_comment_label_plan",
    "build_incremental_comment_label_plan_from_rows",
    "interleave_selected_rows_by_domain",
]
