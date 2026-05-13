from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class DualWriteInput:
    community_name: str
    posts: Sequence[RedditPost]
    trigger_comments_fetch: bool = False
    refresh_posts_latest_after_write: bool = False


@dataclass(slots=True)
class DualWriteDeps:
    db: AsyncSession
    upsert_to_cold_storage: Callable[[str, RedditPost], Awaitable[tuple[bool, bool]]]
    upsert_to_hot_cache: Callable[[str, RedditPost], Awaitable[None]]
    is_current_unique_violation: Callable[[IntegrityError], bool]
    schedule_posts_latest_refresh: Callable[[], None]
    enqueue_comment_backfill: Callable[[str, list[RedditPost]], None]


@dataclass(slots=True)
class DualWriteResult:
    new_count: int
    updated_count: int
    duplicate_count: int


async def execute_dual_write(
    write_input: DualWriteInput,
    deps: DualWriteDeps,
) -> DualWriteResult:
    new_count = 0
    updated_count = 0
    duplicate_count = 0
    new_posts_for_comments: list[RedditPost] = []

    if not deps.db.in_transaction():
        await deps.db.begin()

    for post in write_input.posts:
        try:
            async with deps.db.begin_nested():
                is_new, is_updated = await deps.upsert_to_cold_storage(
                    write_input.community_name,
                    post,
                )
        except IntegrityError as exc:
            if deps.is_current_unique_violation(exc):
                duplicate_count += 1
                continue
            raise

        if is_new:
            new_count += 1
            new_posts_for_comments.append(post)
        elif is_updated:
            updated_count += 1
        else:
            duplicate_count += 1

    try:
        await deps.db.flush()
        await deps.db.commit()
    except Exception:
        await deps.db.rollback()
        raise

    for post in write_input.posts:
        try:
            await deps.upsert_to_hot_cache(write_input.community_name, post)
        except Exception:
            await deps.db.rollback()
        else:
            try:
                await deps.db.commit()
            except Exception:
                await deps.db.rollback()

    if write_input.refresh_posts_latest_after_write and (new_count or updated_count):
        deps.schedule_posts_latest_refresh()

    if write_input.trigger_comments_fetch:
        deps.enqueue_comment_backfill(
            write_input.community_name,
            new_posts_for_comments,
        )

    return DualWriteResult(
        new_count=new_count,
        updated_count=updated_count,
        duplicate_count=duplicate_count,
    )


__all__ = [
    "DualWriteDeps",
    "DualWriteInput",
    "DualWriteResult",
    "execute_dual_write",
]
