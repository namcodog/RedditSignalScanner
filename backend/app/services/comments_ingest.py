from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Iterable, Mapping
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.crawler_runs_service import ensure_crawler_run
from app.utils.subreddit import normalize_subreddit_name, subreddit_key


# process-level cache to avoid重复信息架构探测
_COMMENTS_HAS_EXPIRES: bool | None = None
_COMMENTS_HAS_CRAWL_RUN_ID: bool | None = None
_COMMENTS_HAS_COMMUNITY_RUN_ID: bool | None = None
_COMMENTS_HAS_POST_ID: bool | None = None


# Two SQL variants to be compatible during rollout
COMMENT_UPSERT_SQL_WITH_EXPIRES = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_ID = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at,
        crawl_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at,
        :crawl_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_IDS = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at,
        crawl_run_id, community_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at,
        :crawl_run_id, :community_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        community_run_id = COALESCE(EXCLUDED.community_run_id, comments.community_run_id),
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES_AND_RUN_ID = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at,
        crawl_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at,
        :crawl_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES_AND_RUN_IDS = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at, expires_at,
        crawl_run_id, community_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at, :expires_at,
        :crawl_run_id, :community_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        expires_at = COALESCE(EXCLUDED.expires_at, comments.expires_at),
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        community_run_id = COALESCE(EXCLUDED.community_run_id, comments.community_run_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

COMMENT_UPSERT_SQL_LEGACY = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

COMMENT_UPSERT_SQL_LEGACY_AND_RUN_ID = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at,
        crawl_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at,
        :crawl_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_LEGACY_AND_RUN_IDS = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at,
        crawl_run_id, community_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at,
        :crawl_run_id, :community_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        community_run_id = COALESCE(EXCLUDED.community_run_id, comments.community_run_id),
        post_id = COALESCE(comments.post_id, EXCLUDED.post_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
	    """
	)

COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY_AND_RUN_ID = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at,
        crawl_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at,
        :crawl_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY_AND_RUN_IDS = text(
    """
    INSERT INTO comments (
        reddit_comment_id, source, source_post_id, subreddit,
        source_track, first_seen_at, fetched_at,
        parent_id, depth, body, author_id, author_name, author_created_utc,
        created_utc, score, is_submitter, distinguished, edited,
        permalink, removed_by_category, awards_count,
        lang, business_pool,
        captured_at,
        crawl_run_id, community_run_id
    ) VALUES (
        :reddit_comment_id, :source, :source_post_id, :subreddit,
        :source_track, :first_seen_at, :fetched_at,
        :parent_id, :depth, :body, :author_id, :author_name, :author_created_utc,
        :created_utc, :score, :is_submitter, :distinguished, :edited,
        :permalink, :removed_by_category, :awards_count,
        :lang, :business_pool,
        :captured_at,
        :crawl_run_id, :community_run_id
    )
    ON CONFLICT (reddit_comment_id) DO UPDATE SET
        body = EXCLUDED.body,
        score = EXCLUDED.score,
        edited = EXCLUDED.edited,
        removed_by_category = EXCLUDED.removed_by_category,
        awards_count = EXCLUDED.awards_count,
        crawl_run_id = COALESCE(EXCLUDED.crawl_run_id, comments.crawl_run_id),
        community_run_id = COALESCE(EXCLUDED.community_run_id, comments.community_run_id),
        source_track = COALESCE(EXCLUDED.source_track, comments.source_track),
        first_seen_at = COALESCE(comments.first_seen_at, EXCLUDED.first_seen_at),
        fetched_at = EXCLUDED.fetched_at,
        lang = COALESCE(EXCLUDED.lang, comments.lang),
        business_pool = COALESCE(EXCLUDED.business_pool, comments.business_pool)
    """
)

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _unix_to_datetime(ts: float | int | None) -> datetime | None:
    """Convert Unix timestamp to datetime object."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


async def persist_comments(
    session: AsyncSession,
    *,
    source_post_id: str,
    subreddit: str,
    comments: Iterable[Mapping[str, Any]],
    source: str = "reddit",
    source_track: str = "incremental",
    default_business_pool: str = "lab",
    crawl_run_id: str | None = None,
    community_run_id: str | None = None,
) -> int:
    """Persist a batch of comment dictionaries idempotently.

    Each item is expected to contain at least: id, body, created_utc, depth.
    Optional keys will be defaulted when missing.

    Returns number of processed rows (inserted or updated).
    """
    processed = 0
    # detect expires_at availability once per进程（避免高频批次重复查询信息架构）
    global _COMMENTS_HAS_EXPIRES
    if _COMMENTS_HAS_EXPIRES is None:
        try:
            col_check = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='comments' AND column_name='expires_at'"
                )
            )
            _COMMENTS_HAS_EXPIRES = col_check.first() is not None
        except Exception:
            _COMMENTS_HAS_EXPIRES = False
    has_expires = bool(_COMMENTS_HAS_EXPIRES)

    # detect crawl_run_id availability once per进程（避免重复查询信息架构）
    global _COMMENTS_HAS_CRAWL_RUN_ID
    if _COMMENTS_HAS_CRAWL_RUN_ID is None:
        try:
            col_check = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='comments' AND column_name='crawl_run_id' "
                    "LIMIT 1"
                )
            )
            _COMMENTS_HAS_CRAWL_RUN_ID = col_check.first() is not None
        except Exception:
            _COMMENTS_HAS_CRAWL_RUN_ID = False
    has_crawl_run_id = bool(_COMMENTS_HAS_CRAWL_RUN_ID)
    if has_crawl_run_id and crawl_run_id:
        try:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={"source_track": source_track, "source_post_id": source_post_id},
            )
        except Exception:
            # Best-effort: do not block ingestion if run tracking table is missing/drifted.
            pass

    global _COMMENTS_HAS_POST_ID
    if _COMMENTS_HAS_POST_ID is None:
        try:
            col_check = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='comments' AND column_name='post_id' "
                    "LIMIT 1"
                )
            )
            _COMMENTS_HAS_POST_ID = col_check.first() is not None
        except Exception:
            _COMMENTS_HAS_POST_ID = False
    has_post_id = bool(_COMMENTS_HAS_POST_ID)

    # community_run_id depends on new schema (best-effort / optional)
    global _COMMENTS_HAS_COMMUNITY_RUN_ID
    if _COMMENTS_HAS_COMMUNITY_RUN_ID is None:
        try:
            col_check = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='comments' AND column_name='community_run_id' "
                    "LIMIT 1"
                )
            )
            _COMMENTS_HAS_COMMUNITY_RUN_ID = col_check.first() is not None
        except Exception:
            _COMMENTS_HAS_COMMUNITY_RUN_ID = False
    has_community_run_id = bool(_COMMENTS_HAS_COMMUNITY_RUN_ID and has_crawl_run_id)

    # 统一计算 subreddit 与 comments_retention_days，避免在循环中重复 get_settings
    normalized_subreddit = subreddit_key(subreddit)
    try:
        settings = get_settings()
        retention_days = int(getattr(settings, "comments_retention_days", 180))
    except Exception:
        retention_days = 180

    post_id = None
    if has_post_id:
        # Some schemas store an internal FK `comments.post_id` (NOT NULL). Resolve it once.
        try:
            res = await session.execute(
                text(
                    "SELECT id FROM posts_raw WHERE source = :source AND source_post_id = :source_post_id "
                    "AND is_current = true ORDER BY id DESC LIMIT 1"
                ),
                {"source": source, "source_post_id": source_post_id},
            )
            post_id = res.scalar()
        except Exception:
            post_id = None

        if post_id is None:
            return 0

    authors: dict[str, dict[str, Any]] = {}
    for c in comments:
        # Convert Unix timestamps to datetime objects
        created_utc_raw = c.get("created_utc")
        created_utc = _unix_to_datetime(created_utc_raw) if created_utc_raw else _now_utc()

        author_created_utc_raw = c.get("author_created_utc")
        author_created_utc = _unix_to_datetime(author_created_utc_raw)

        captured_at = c.get("captured_at") or _now_utc()
        expires_at = captured_at + timedelta(days=max(1, retention_days))
        lang = c.get("lang")
        biz_pool = c.get("business_pool") or default_business_pool

        params = {
            "reddit_comment_id": str(c.get("id")),
            "source": source,
            "source_post_id": source_post_id,
            "subreddit": normalized_subreddit,
            "source_track": source_track,
            "first_seen_at": captured_at,
            "fetched_at": captured_at,
            "parent_id": c.get("parent_id"),
            "depth": int(c.get("depth", 0) or 0),
            "body": c.get("body") or "",
            "author_id": (c.get("author_id") or c.get("author")),
            "author_name": c.get("author_name") or c.get("author"),
            "author_created_utc": author_created_utc,
            "created_utc": created_utc,
            "score": int(c.get("score", 0) or 0),
            "is_submitter": bool(c.get("is_submitter", False)),
            "distinguished": c.get("distinguished"),
            "edited": bool(c.get("edited", False)),
            "permalink": c.get("permalink"),
            "removed_by_category": c.get("removed_by_category"),
            "awards_count": int(c.get("awards_count", 0) or 0),
            "captured_at": captured_at,
            "expires_at": expires_at,
            "lang": lang,
            "business_pool": biz_pool,
        }
        if has_post_id:
            params["post_id"] = post_id
        if has_crawl_run_id:
            params["crawl_run_id"] = crawl_run_id
        if has_community_run_id:
            params["community_run_id"] = community_run_id

        # basic validation
        if not params["reddit_comment_id"]:
            continue
        if not params["body"]:
            # keep structure but avoid empty bodies breaking NOT NULL
            params["body"] = "[deleted]"

        if has_expires and has_crawl_run_id and has_community_run_id:
            await session.execute(
                COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_IDS
                if has_post_id
                else COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES_AND_RUN_IDS,
                params,
            )
        elif has_expires and has_crawl_run_id:
            await session.execute(
                COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_ID
                if has_post_id
                else COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES_AND_RUN_ID,
                params,
            )
        elif has_expires:
            await session.execute(
                COMMENT_UPSERT_SQL_WITH_EXPIRES
                if has_post_id
                else COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES,
                params,
            )
        else:
            legacy_params = params.copy()
            legacy_params.pop("expires_at", None)
            if has_crawl_run_id and has_community_run_id:
                await session.execute(
                    COMMENT_UPSERT_SQL_LEGACY_AND_RUN_IDS
                    if has_post_id
                    else COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY_AND_RUN_IDS,
                    legacy_params,
                )
            elif has_crawl_run_id:
                await session.execute(
                    COMMENT_UPSERT_SQL_LEGACY_AND_RUN_ID
                    if has_post_id
                    else COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY_AND_RUN_ID,
                    legacy_params,
                )
            else:
                legacy_params.pop("crawl_run_id", None)
                legacy_params.pop("community_run_id", None)
                await session.execute(
                    COMMENT_UPSERT_SQL_LEGACY
                    if has_post_id
                    else COMMENT_UPSERT_SQL_NO_POST_ID_LEGACY,
                    legacy_params,
                )
        # collect author info for upsert
        aid = params.get("author_id") or params.get("author_name")
        # Skip ultra-common placeholders to avoid hot-row contention
        if aid and str(aid).strip().lower() not in {"[deleted]", "automoderator"}:
            authors[str(aid)] = {
                "author_id": str(aid),
                "author_name": params.get("author_name"),
                "created_utc": params.get("author_created_utc"),
                "first_seen_at_global": params.get("captured_at"),
            }
        processed += 1

    # upsert authors (best-effort，使用单独的短事务，避免与主事务形成死锁)
    if authors:
        logger = logging.getLogger(__name__)
        try:
            async with SessionFactory() as author_session:
                for a in authors.values():
                    await author_session.execute(
                        text(
                            """
                            INSERT INTO authors (author_id, author_name, created_utc, is_bot, first_seen_at_global)
                            VALUES (:author_id, :author_name, :created_utc, false, :first_seen_at_global)
                            ON CONFLICT (author_id) DO NOTHING
                            """
                        ),
                        a,
                    )
                await author_session.commit()
        except SQLAlchemyError as exc:
            # 作者表仅用于分析统计，插入失败时不影响评论主流程，避免死锁拖垮回填
            logger.warning("Author upsert failed (ignored): %s", exc)

    return processed
