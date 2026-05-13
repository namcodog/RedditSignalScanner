from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posts_storage import PostHot
from app.services.infrastructure.reddit_client import RedditPost
from app.utils.subreddit import subreddit_key


@dataclass(slots=True)
class HotCacheUpsertInput:
    community_name: str
    post: RedditPost
    hot_cache_ttl_hours: int


@dataclass(slots=True)
class HotCacheUpsertDeps:
    db: AsyncSession
    ensure_author: Callable[[str | None, str | None], Awaitable[None]]
    unix_to_datetime: Callable[[float], datetime]


async def upsert_post_to_hot_cache(
    write_input: HotCacheUpsertInput,
    deps: HotCacheUpsertDeps,
) -> None:
    post = write_input.post
    await deps.ensure_author(post.author, post.author)

    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=write_input.hot_cache_ttl_hours
    )
    norm_sub = subreddit_key(write_input.community_name)

    base_values = dict(
        source="reddit",
        source_post_id=post.id,
        created_at=deps.unix_to_datetime(post.created_utc),
        cached_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        author_id=post.author,
        author_name=post.author,
        title=post.title,
        body=post.selftext or "",
        subreddit=norm_sub,
        score=post.score,
        num_comments=post.num_comments,
    )

    stmt = pg_insert(PostHot).values(
        **base_values,
        **{PostHot.extra_data.key: {"permalink": post.permalink}},
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_post_id"],
        set_={
            "cached_at": stmt.excluded.cached_at,
            "expires_at": stmt.excluded.expires_at,
            "author_id": stmt.excluded.author_id,
            "author_name": stmt.excluded.author_name,
            "score": stmt.excluded.score,
            "num_comments": stmt.excluded.num_comments,
            "title": stmt.excluded.title,
            "body": stmt.excluded.body,
            "metadata": stmt.excluded.metadata,
        },
    )

    try:
        await deps.db.execute(stmt)
    except Exception as exc:
        if "no unique or exclusion constraint" not in str(exc):
            raise

        await deps.db.rollback()

        existing = await deps.db.execute(
            select(PostHot).where(
                PostHot.source == "reddit",
                PostHot.source_post_id == post.id,
            )
        )
        row = existing.scalars().first()
        if row:
            await deps.db.execute(
                update(PostHot)
                .where(PostHot.id == row.id)
                .values(
                    **base_values,
                    **{PostHot.extra_data.key: {"permalink": post.permalink}},
                )
            )
        else:
            await deps.db.execute(
                pg_insert(PostHot).values(
                    **base_values,
                    **{PostHot.extra_data.key: {"permalink": post.permalink}},
                )
            )


__all__ = [
    "HotCacheUpsertDeps",
    "HotCacheUpsertInput",
    "upsert_post_to_hot_cache",
]
