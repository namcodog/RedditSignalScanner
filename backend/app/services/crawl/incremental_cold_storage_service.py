from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posts_storage import PostRaw
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.infrastructure.reddit_client import RedditPost
from app.utils.subreddit import subreddit_key

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ColdStorageUpsertInput:
    community_name: str
    post: RedditPost
    source_track: str
    crawl_run_id: str | None
    community_run_id: str | None
    duplicate_mode: str
    spam_categories: Mapping[str, str | None]
    crawler_run_row_ensured: bool


@dataclass(slots=True)
class ColdStorageUpsertDeps:
    db: AsyncSession
    ensure_author: Callable[[str | None, str | None], Awaitable[None]]
    find_content_duplicate: Callable[[str, RedditPost], Awaitable[str | None]]
    unix_to_datetime: Callable[[float], datetime]
    posts_raw_has_crawl_run_id: Callable[[AsyncSession], Awaitable[bool]]
    posts_raw_has_community_run_id: Callable[[AsyncSession], Awaitable[bool]]


@dataclass(slots=True)
class ColdStorageUpsertResult:
    is_new: bool
    is_updated: bool
    crawler_run_row_ensured: bool


async def upsert_post_to_cold_storage(
    write_input: ColdStorageUpsertInput,
    deps: ColdStorageUpsertDeps,
) -> ColdStorageUpsertResult:
    now = datetime.now(timezone.utc)
    post = write_input.post
    created_at = deps.unix_to_datetime(post.created_utc)

    if post.author:
        await deps.ensure_author(post.author, post.author)
        author_id = post.author
        author_name = post.author
    else:
        author_id = None
        author_name = None

    existing_row = await deps.db.execute(
        text(
            """
            SELECT id, version, score, num_comments, title, body, is_current
            FROM posts_raw
            WHERE source = 'reddit' AND source_post_id = :pid
            ORDER BY version DESC
            LIMIT 1
            """
        ),
        {"pid": post.id},
    )
    existing_post = existing_row.mappings().first()

    norm_sub = subreddit_key(write_input.community_name)
    base_values: dict[str, Any] = {
        "source": "reddit",
        "source_post_id": post.id,
        "created_at": created_at,
        "fetched_at": now,
        "first_seen_at": now,
        "source_track": write_input.source_track,
        "author_id": author_id,
        "author_name": author_name,
        "title": post.title,
        "body": post.selftext or "",
        "url": post.url,
        "subreddit": norm_sub,
        "score": post.score,
        "num_comments": post.num_comments,
        "is_current": True,
        "valid_from": now,
        "spam_category": getattr(post, "spam_category", None),
    }

    has_run_col = await deps.posts_raw_has_crawl_run_id(deps.db)
    include_run_id = bool(has_run_col and write_input.crawl_run_id)
    has_community_run_col = await deps.posts_raw_has_community_run_id(deps.db)
    include_community_run_id = bool(has_community_run_col and write_input.community_run_id)

    crawler_run_row_ensured = write_input.crawler_run_row_ensured
    if include_run_id and write_input.crawl_run_id and not crawler_run_row_ensured:
        await ensure_crawler_run(
            deps.db,
            crawl_run_id=write_input.crawl_run_id,
            config={"mode": "incremental", "source_track": write_input.source_track},
        )
        crawler_run_row_ensured = True
    if include_run_id and write_input.crawl_run_id:
        base_values["crawl_run_id"] = write_input.crawl_run_id
    if include_community_run_id and write_input.community_run_id:
        base_values["community_run_id"] = write_input.community_run_id

    metadata_payload = {
        "permalink": post.permalink,
        "upvote_ratio": getattr(post, "upvote_ratio", None),
    }
    spam_category = getattr(post, "spam_category", None)
    if not spam_category:
        spam_category = write_input.spam_categories.get(str(post.id))
    if spam_category:
        metadata_payload["spam_category"] = spam_category
    if write_input.crawl_run_id:
        metadata_payload["run_id"] = write_input.crawl_run_id
    if write_input.community_run_id:
        metadata_payload["community_run_id"] = write_input.community_run_id

    if existing_post is None:
        duplicate_of = None
        is_duplicate = False
        if write_input.duplicate_mode != "allow":
            duplicate_of = await deps.find_content_duplicate(norm_sub, post)
        if duplicate_of:
            if write_input.duplicate_mode == "drop":
                logger.info(
                    "♻️ Post %s content-duplicate of %s in %s, skip insert",
                    post.id,
                    duplicate_of,
                    norm_sub,
                )
                return ColdStorageUpsertResult(
                    is_new=False,
                    is_updated=False,
                    crawler_run_row_ensured=crawler_run_row_ensured,
                )
            metadata_payload["duplicate_of"] = duplicate_of
            metadata_payload["is_duplicate"] = True
            is_duplicate = True

        extra_columns = ""
        extra_values = ""
        if include_run_id:
            extra_columns += ", crawl_run_id"
            extra_values += ", :crawl_run_id"
        if include_community_run_id:
            extra_columns += ", community_run_id"
            extra_values += ", :community_run_id"
        sql = text(
            f"""
            INSERT INTO posts_raw (
                source, source_post_id, version, edit_count,
                created_at, fetched_at, first_seen_at, source_track,
                author_id, author_name,
                title, body, url, subreddit, score, num_comments,
                is_current, valid_from, valid_to, metadata{extra_columns}
            ) VALUES (
                :source, :source_post_id, 1, 0,
                :created_at, :fetched_at, :first_seen_at, :source_track,
                :author_id, :author_name,
                :title, :body, :url, :subreddit, :score, :num_comments,
                TRUE, :valid_from, '9999-12-31'::timestamptz, :metadata{extra_values}
            )
            ON CONFLICT (source, source_post_id, version)
            DO UPDATE SET fetched_at = EXCLUDED.fetched_at
            """
        )
        params = {
            **base_values,
            "valid_to": None,
            "metadata": json.dumps(metadata_payload),
        }
        await deps.db.execute(sql, params)
        return ColdStorageUpsertResult(
            is_new=not is_duplicate,
            is_updated=False,
            crawler_run_row_ensured=crawler_run_row_ensured,
        )

    body_text = post.selftext or ""
    has_changes = any(
        [
            existing_post["score"] != post.score,
            existing_post["num_comments"] != post.num_comments,
            existing_post["title"] != post.title,
            (existing_post["body"] or "") != body_text,
        ]
    )

    if not has_changes:
        extra_update = ""
        if include_run_id:
            extra_update += ", crawl_run_id = :crawl_run_id"
        if include_community_run_id:
            extra_update += ", community_run_id = :community_run_id"
        await deps.db.execute(
            text(
                f"""
                UPDATE posts_raw
                SET fetched_at = :fetched_at,
                    metadata = :metadata{extra_update}
                WHERE source = :source
                  AND source_post_id = :source_post_id
                  AND version = :version
                """
            ),
            {
                "source": base_values["source"],
                "source_post_id": base_values["source_post_id"],
                "fetched_at": base_values["fetched_at"],
                "version": existing_post["version"],
                "metadata": json.dumps(metadata_payload),
                "crawl_run_id": write_input.crawl_run_id,
                "community_run_id": write_input.community_run_id,
            },
        )
        return ColdStorageUpsertResult(
            is_new=False,
            is_updated=False,
            crawler_run_row_ensured=crawler_run_row_ensured,
        )

    max_version_row = await deps.db.execute(
        select(func.max(PostRaw.version)).where(
            PostRaw.source == "reddit",
            PostRaw.source_post_id == post.id,
        )
    )
    next_version = (max_version_row.scalar() or 0) + 1
    await deps.db.execute(
        text(
            """
            UPDATE posts_raw
            SET is_current = FALSE, valid_to = :valid_to
            WHERE source = 'reddit' AND source_post_id = :pid AND is_current = TRUE
            """
        ),
        {"valid_to": now, "pid": post.id},
    )
    await deps.db.flush()
    extra_columns = ""
    extra_values = ""
    extra_update = ""
    if include_run_id:
        extra_columns += ", crawl_run_id"
        extra_values += ", :crawl_run_id"
        extra_update += ", crawl_run_id = EXCLUDED.crawl_run_id"
    if include_community_run_id:
        extra_columns += ", community_run_id"
        extra_values += ", :community_run_id"
        extra_update += ", community_run_id = EXCLUDED.community_run_id"
    insert_sql = text(
        f"""
        INSERT INTO posts_raw (
            source, source_post_id, version, edit_count,
            created_at, fetched_at, first_seen_at, source_track,
            author_id, author_name,
            title, body, url, subreddit, score, num_comments,
            is_current, valid_from, valid_to, metadata{extra_columns}
        ) VALUES (
            :source, :source_post_id, :version, :edit_count,
            :created_at, :fetched_at, :first_seen_at, :source_track,
            :author_id, :author_name,
            :title, :body, :url, :subreddit, :score, :num_comments,
            TRUE, :valid_from, '9999-12-31'::timestamptz, :metadata{extra_values}
        )
        ON CONFLICT (source, source_post_id, version)
        DO UPDATE SET
            fetched_at = EXCLUDED.fetched_at,
            is_current = EXCLUDED.is_current,
            valid_from = EXCLUDED.valid_from,
            valid_to = EXCLUDED.valid_to,
            edit_count = EXCLUDED.edit_count,
            score = EXCLUDED.score,
            num_comments = EXCLUDED.num_comments,
            title = EXCLUDED.title,
            body = EXCLUDED.body,
            metadata = EXCLUDED.metadata{extra_update}
        """
    )
    params = {
        **base_values,
        "version": next_version,
        "edit_count": (existing_post.get("edit_count") or 0) + 1
        if isinstance(existing_post, dict)
        else (getattr(existing_post, "edit_count", 0) or 0) + 1,
        "metadata": json.dumps(metadata_payload),
    }
    await deps.db.execute(insert_sql, params)
    return ColdStorageUpsertResult(
        is_new=False,
        is_updated=True,
        crawler_run_row_ensured=crawler_run_row_ensured,
    )


__all__ = [
    "ColdStorageUpsertDeps",
    "ColdStorageUpsertInput",
    "ColdStorageUpsertResult",
    "upsert_post_to_cold_storage",
]
