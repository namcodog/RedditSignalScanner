from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

from sqlalchemy import text


@dataclass(frozen=True)
class CommentEvidenceArtifacts:
    sample_comments_db: list[dict[str, Any]]
    comment_counts_by_subreddit: Counter[str]
    posts_db_current: int
    comments_db_total: int
    comments_db_eligible: int
    comments_pipeline_status: str
    remediation_actions: list[dict[str, Any]]


def build_sample_posts_db(
    deduped_posts: Sequence[dict[str, Any]],
    *,
    normalise_community_name: Callable[[str], str],
    limit: int = 50,
) -> list[dict[str, Any]]:
    try:
        ranked = sorted(
            deduped_posts,
            key=lambda p: int(p.get("score", 0) or 0),
            reverse=True,
        )
    except Exception:
        ranked = list(deduped_posts)

    sample_posts_db: list[dict[str, Any]] = []
    for row in ranked[:limit]:
        title = str(row.get("title") or "").strip()
        summary = str(row.get("summary") or "").strip()
        if not title and not summary:
            continue
        combined = f"{title} {summary}".strip()
        raw_subreddit = str(row.get("subreddit") or "").strip()
        subreddit = normalise_community_name(raw_subreddit) if raw_subreddit else "unknown"
        sample_posts_db.append(
            {
                "id": str(row.get("id") or ""),
                "title": combined,
                "text": combined,
                "body": summary,
                "subreddit": subreddit,
                "author": row.get("author"),
                "score": int(row.get("score") or 0),
                "url": row.get("url"),
                "permalink": row.get("permalink"),
            }
        )
    return sample_posts_db


def derive_comments_pipeline_status(
    *,
    sample_comments_db: Sequence[dict[str, Any]],
    comments_db_total: int,
    comments_db_eligible: int,
) -> str:
    if sample_comments_db:
        return "ok"
    if comments_db_total <= 0:
        return "disabled"
    if comments_db_eligible <= 0:
        return "all_noise"
    return "filtered"


async def fetch_comment_evidence(
    *,
    task: Any,
    topic_profile: Any,
    deduped_posts: Sequence[dict[str, Any]],
    session_factory: Callable[[], Any],
    normalise_community_name: Callable[[str], str],
    filter_items_by_profile_context_fn: Callable[..., Sequence[dict[str, Any]]],
    schedule_auto_backfill_for_missing_comments_fn: Callable[..., Awaitable[list[dict[str, Any]]]],
    limit: int = 200,
    output_limit: int = 50,
) -> CommentEvidenceArtifacts:
    sample_comments_db: list[dict[str, Any]] = []
    comment_counts_by_subreddit: Counter[str] = Counter()
    posts_db_current = 0
    comments_db_total = 0
    comments_db_eligible = 0
    comments_pipeline_status = "unknown"
    remediation_actions: list[dict[str, Any]] = []

    source_ids = [
        str(post.get("id") or "").strip()
        for post in deduped_posts
        if str(post.get("id") or "").strip()
    ]
    unique_source_ids = list(dict.fromkeys(source_ids))
    if not unique_source_ids:
        return CommentEvidenceArtifacts(
            sample_comments_db=sample_comments_db,
            comment_counts_by_subreddit=comment_counts_by_subreddit,
            posts_db_current=posts_db_current,
            comments_db_total=comments_db_total,
            comments_db_eligible=comments_db_eligible,
            comments_pipeline_status="disabled",
            remediation_actions=remediation_actions,
        )

    try:
        async with session_factory() as session:
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
                LIMIT :limit
                """
                ),
                {"source_ids": unique_source_ids, "limit": limit},
            )
            for row in result.mappings().all():
                body = str(row.get("body") or "").strip()
                if not body:
                    continue
                raw_subreddit = str(row.get("subreddit") or "").strip()
                subreddit = normalise_community_name(raw_subreddit) if raw_subreddit else "unknown"
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
    except Exception:
        comments_pipeline_status = "disabled"

    if topic_profile is not None and sample_comments_db:
        if bool(getattr(topic_profile, "require_context_for_fetch", False)):
            sample_comments_db = list(
                filter_items_by_profile_context_fn(
                    sample_comments_db,
                    topic_profile,
                    text_keys=("text", "body"),
                )
            )

    sample_comments_db = sample_comments_db[:output_limit]
    for item in sample_comments_db:
        name = str(item.get("subreddit") or "").strip() or "unknown"
        comment_counts_by_subreddit[name] += 1

    if topic_profile is not None and not sample_comments_db:
        try:
            remediation_actions = await schedule_auto_backfill_for_missing_comments_fn(
                task=task,
                topic_profile=topic_profile,
                posts=deduped_posts,
            )
        except Exception:
            remediation_actions = []

    comments_pipeline_status = derive_comments_pipeline_status(
        sample_comments_db=sample_comments_db,
        comments_db_total=comments_db_total,
        comments_db_eligible=comments_db_eligible,
    )

    return CommentEvidenceArtifacts(
        sample_comments_db=sample_comments_db,
        comment_counts_by_subreddit=comment_counts_by_subreddit,
        posts_db_current=posts_db_current,
        comments_db_total=comments_db_total,
        comments_db_eligible=comments_db_eligible,
        comments_pipeline_status=comments_pipeline_status,
        remediation_actions=remediation_actions,
    )
