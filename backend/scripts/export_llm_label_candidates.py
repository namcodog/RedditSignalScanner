from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text as sqltext

from app.core.config import get_settings
from app.tasks.llm_label_task import (
    _LOW_SCORE_MAX,
    _fetch_comment_candidates,
    _fetch_post_candidates,
    _fetch_top_comments,
)
from app.db.session import SessionFactory
from app.utils.asyncio_runner import run as run_coro

_DEFAULT_NOISE_RATIO = 0.1
_DEFAULT_NOISE_MIN_SCORE = 20
_DEFAULT_NOISE_MIN_COMMENTS = 10


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _export_posts(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    max_comment_chars: int,
    top_comments: int,
) -> list[dict[str, Any]]:
    rows = run_coro(_fetch_post_candidates(limit, lookback_days)) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source") or "reddit")
        source_post_id = str(row.get("source_post_id") or "")
        comments = []
        if source_post_id:
            comments = run_coro(
                _fetch_top_comments(source, source_post_id, top_comments)
            ) or []
        payload.append(
            {
                "task_type": "post_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "title": _truncate(str(row.get("title") or ""), max_body_chars),
                "body": _truncate(str(row.get("body") or ""), max_body_chars),
                "comments": [
                    _truncate(str(c or ""), max_comment_chars) for c in comments[:top_comments]
                ],
            }
        )
    return payload


async def _fetch_post_candidates_all(
    *,
    limit: int,
    lookback_days: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
    noise_min_comments: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"days": int(lookback_days)}
    limit_clause = ""
    if limit > 0:
        limit_clause = "LIMIT :limit"
        params["limit"] = int(limit)

    core_sql = f"""
        SELECT p.id,
               p.title,
               p.body,
               p.subreddit,
               p.score,
               p.num_comments,
               p.text_norm_hash,
               p.source,
               p.source_post_id,
               p.url,
               ps.value_score,
               ps.business_pool
        FROM posts_raw p
        JOIN post_scores_latest_v ps ON ps.post_id = p.id
        LEFT JOIN post_llm_labels llm ON llm.post_id = p.id
        LEFT JOIN post_llm_labels llm_hash
          ON p.text_norm_hash IS NOT NULL
         AND llm_hash.text_norm_hash = p.text_norm_hash
        WHERE p.is_current = TRUE
          AND ps.business_pool IN ('core','lab')
          AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
          AND llm.post_id IS NULL
          AND llm_hash.post_id IS NULL
        ORDER BY ps.value_score DESC, p.score DESC, p.num_comments DESC
        {limit_clause}
    """

    async with SessionFactory() as session:
        result = await session.execute(sqltext(core_sql), params)
        rows = [dict(row) for row in result.mappings().all()]

        if include_noise and noise_ratio > 0:
            base_count = int(limit) if limit > 0 else await _count_post_candidates_core_lab(
                session=session,
                lookback_days=lookback_days,
            )
            noise_limit = int(base_count * noise_ratio)
            if noise_limit > 0:
                noise_params = {
                    "days": int(lookback_days),
                    "min_score": int(noise_min_score),
                    "min_comments": int(noise_min_comments),
                    "limit": int(noise_limit),
                }
                noise_sql = """
                    SELECT p.id,
                           p.title,
                           p.body,
                           p.subreddit,
                           p.score,
                           p.num_comments,
                           p.text_norm_hash,
                           p.source,
                           p.source_post_id,
                           p.url,
                           ps.value_score,
                           ps.business_pool
                    FROM posts_raw p
                    JOIN post_scores_latest_v ps ON ps.post_id = p.id
                    LEFT JOIN post_llm_labels llm ON llm.post_id = p.id
                    LEFT JOIN post_llm_labels llm_hash
                      ON p.text_norm_hash IS NOT NULL
                     AND llm_hash.text_norm_hash = p.text_norm_hash
                    WHERE p.is_current = TRUE
                      AND ps.business_pool = 'noise'
                      AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.post_id IS NULL
                      AND llm_hash.post_id IS NULL
                      AND (p.score >= :min_score OR p.num_comments >= :min_comments)
                    ORDER BY p.score DESC, p.num_comments DESC
                    LIMIT :limit
                """
                noise_result = await session.execute(sqltext(noise_sql), noise_params)
                rows.extend(dict(row) for row in noise_result.mappings().all())
        return rows


async def _count_post_candidates_core_lab(
    *,
    session,
    lookback_days: int,
) -> int:
    result = await session.execute(
        sqltext(
            """
            SELECT COUNT(*)
            FROM posts_raw p
            JOIN post_scores_latest_v ps ON ps.post_id = p.id
            LEFT JOIN post_llm_labels llm ON llm.post_id = p.id
            LEFT JOIN post_llm_labels llm_hash
              ON p.text_norm_hash IS NOT NULL
             AND llm_hash.text_norm_hash = p.text_norm_hash
            WHERE p.is_current = TRUE
              AND ps.business_pool IN ('core','lab')
              AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
              AND llm.post_id IS NULL
              AND llm_hash.post_id IS NULL
            """
        ),
        {"days": int(lookback_days)},
    )
    return int(result.scalar_one())


def _export_posts_all(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    max_comment_chars: int,
    top_comments: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
    noise_min_comments: int,
) -> list[dict[str, Any]]:
    rows = run_coro(
        _fetch_post_candidates_all(
            limit=limit,
            lookback_days=lookback_days,
            include_noise=include_noise,
            noise_ratio=noise_ratio,
            noise_min_score=noise_min_score,
            noise_min_comments=noise_min_comments,
        )
    ) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source") or "reddit")
        source_post_id = str(row.get("source_post_id") or "")
        comments = []
        if source_post_id:
            comments = run_coro(
                _fetch_top_comments(source, source_post_id, top_comments)
            ) or []
        payload.append(
            {
                "task_type": "post_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "title": _truncate(str(row.get("title") or ""), max_body_chars),
                "body": _truncate(str(row.get("body") or ""), max_body_chars),
                "comments": [
                    _truncate(str(c or ""), max_comment_chars)
                    for c in comments[:top_comments]
                ],
            }
        )
    return payload


def _export_comments(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
) -> list[dict[str, Any]]:
    rows = run_coro(_fetch_comment_candidates(limit, lookback_days)) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        payload.append(
            {
                "task_type": "comment_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "post_title": _truncate(str(row.get("post_title") or ""), max_body_chars),
                "comment_body": _truncate(str(row.get("body") or ""), max_body_chars),
            }
        )
    return payload


async def _fetch_comment_candidates_all(
    *,
    limit: int,
    lookback_days: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"days": int(lookback_days)}
    limit_clause = ""
    if limit > 0:
        limit_clause = "LIMIT :limit"
        params["limit"] = int(limit)

    core_sql = f"""
        SELECT c.id,
               c.body,
               c.subreddit,
               c.score,
               c.source,
               c.source_post_id,
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
        ORDER BY cs.value_score DESC, c.score DESC
        {limit_clause}
    """

    async with SessionFactory() as session:
        result = await session.execute(sqltext(core_sql), params)
        rows = [dict(row) for row in result.mappings().all()]

        if include_noise and noise_ratio > 0:
            base_count = int(limit) if limit > 0 else await _count_comment_candidates_core_lab(
                session=session,
                lookback_days=lookback_days,
            )
            noise_limit = int(base_count * noise_ratio)
            if noise_limit > 0:
                noise_params = {
                    "days": int(lookback_days),
                    "min_score": int(noise_min_score),
                    "limit": int(noise_limit),
                }
                noise_sql = """
                    SELECT c.id,
                           c.body,
                           c.subreddit,
                           c.score,
                           c.source,
                           c.source_post_id,
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
                    WHERE cs.business_pool = 'noise'
                      AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.comment_id IS NULL
                      AND c.score >= :min_score
                    ORDER BY c.score DESC
                    LIMIT :limit
                """
                noise_result = await session.execute(sqltext(noise_sql), noise_params)
                rows.extend(dict(row) for row in noise_result.mappings().all())
        return rows


async def _count_comment_candidates_core_lab(
    *,
    session,
    lookback_days: int,
) -> int:
    result = await session.execute(
        sqltext(
            """
            SELECT COUNT(*)
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
            """
        ),
        {"days": int(lookback_days)},
    )
    return int(result.scalar_one())


def _export_comments_all(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
) -> list[dict[str, Any]]:
    rows = run_coro(
        _fetch_comment_candidates_all(
            limit=limit,
            lookback_days=lookback_days,
            include_noise=include_noise,
            noise_ratio=noise_ratio,
            noise_min_score=noise_min_score,
        )
    ) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        payload.append(
            {
                "task_type": "comment_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "post_title": _truncate(str(row.get("post_title") or ""), max_body_chars),
                "comment_body": _truncate(str(row.get("body") or ""), max_body_chars),
            }
        )
    return payload


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Export LLM label candidates.")
    parser.add_argument("--output-dir", default="reports/llm-client")
    parser.add_argument("--post-limit", type=int, default=settings.llm_label_post_limit)
    parser.add_argument(
        "--comment-limit", type=int, default=settings.llm_label_comment_limit
    )
    parser.add_argument(
        "--lookback-days", type=int, default=settings.llm_label_lookback_days
    )
    parser.add_argument("--export-all", action="store_true")
    parser.add_argument("--include-noise", action="store_true")
    parser.add_argument("--noise-ratio", type=float, default=_DEFAULT_NOISE_RATIO)
    parser.add_argument("--noise-min-score", type=int, default=_DEFAULT_NOISE_MIN_SCORE)
    parser.add_argument(
        "--noise-min-comments", type=int, default=_DEFAULT_NOISE_MIN_COMMENTS
    )
    parser.add_argument("--top-comments", type=int, default=2)
    parser.add_argument("--posts-only", action="store_true")
    parser.add_argument("--comments-only", action="store_true")
    args = parser.parse_args()

    if args.posts_only and args.comments_only:
        raise SystemExit("Choose only one of --posts-only or --comments-only.")

    output_dir = Path(args.output_dir)
    max_body_chars = int(settings.llm_label_body_chars)
    max_comment_chars = int(settings.llm_label_comment_chars)

    post_limit = int(args.post_limit)
    comment_limit = int(args.comment_limit)
    if args.export_all and post_limit <= 0:
        post_limit = 0
    if args.export_all and comment_limit <= 0:
        comment_limit = 0

    posts_payload: list[dict[str, Any]] = []
    comments_payload: list[dict[str, Any]] = []

    if not args.comments_only:
        if args.export_all:
            posts_payload = _export_posts_all(
                limit=post_limit,
                lookback_days=int(args.lookback_days),
                max_body_chars=max_body_chars,
                max_comment_chars=max_comment_chars,
                top_comments=int(args.top_comments),
                include_noise=bool(args.include_noise),
                noise_ratio=float(args.noise_ratio),
                noise_min_score=int(args.noise_min_score),
                noise_min_comments=int(args.noise_min_comments),
            )
        else:
            posts_payload = _export_posts(
                limit=post_limit,
                lookback_days=int(args.lookback_days),
                max_body_chars=max_body_chars,
                max_comment_chars=max_comment_chars,
                top_comments=int(args.top_comments),
            )

    if not args.posts_only:
        if args.export_all:
            comments_payload = _export_comments_all(
                limit=comment_limit,
                lookback_days=int(args.lookback_days),
                max_body_chars=max_body_chars,
                include_noise=bool(args.include_noise),
                noise_ratio=float(args.noise_ratio),
                noise_min_score=int(args.noise_min_score),
            )
        else:
            comments_payload = _export_comments(
                limit=comment_limit,
                lookback_days=int(args.lookback_days),
                max_body_chars=max_body_chars,
            )

    posts_path = output_dir / "posts_batch_001.jsonl"
    comments_path = output_dir / "comments_batch_001.jsonl"
    if posts_payload:
        _write_jsonl(posts_path, posts_payload)
    if comments_payload:
        _write_jsonl(comments_path, comments_payload)

    print(
        json.dumps(
            {
                "status": "ok",
                "posts": len(posts_payload),
                "comments": len(comments_payload),
                "posts_path": str(posts_path) if posts_payload else None,
                "comments_path": str(comments_path) if comments_payload else None,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
