from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.task import Task
from app.schemas.task import TaskSummary


class _CommunityProfileLike(Protocol):
    name: str
    daily_posts: float | int | None
    avg_comment_length: float | int | None


class _CollectedCommunityLike(Protocol):
    profile: _CommunityProfileLike
    posts: Sequence[object]


@dataclass(frozen=True)
class DiscoveredCommunityRecordResult:
    status: str
    reason: str | None = None
    upserted_count: int = 0


def _normalise_community_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        return "r/unknown"
    if name.lower().startswith("r/"):
        name = name[2:]
    name = name.lstrip("/")
    return f"r/{name.lower()}"


async def _task_exists(task_id: object) -> bool:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Task.id).where(Task.id == task_id).limit(1)
        )
        return result.scalar_one_or_none() is not None


async def record_discovered_communities_for_task(
    *,
    task: TaskSummary,
    collected: Sequence[_CollectedCommunityLike],
    keywords: Sequence[str],
) -> DiscoveredCommunityRecordResult:
    if not collected:
        return DiscoveredCommunityRecordResult(
            status="skipped",
            reason="no_collected_communities",
        )
    if task.user_id is None:
        return DiscoveredCommunityRecordResult(
            status="skipped",
            reason="transient_task_context",
        )
    if not await _task_exists(task.id):
        return DiscoveredCommunityRecordResult(
            status="skipped",
            reason="task_not_persisted",
        )

    now = datetime.now(timezone.utc)
    keywords_payload = {"keywords": list(keywords)}
    upserted_count = 0

    async with SessionFactory() as session:
        for entry in collected:
            mention_count = len(entry.posts)
            if mention_count <= 0:
                continue
            name = _normalise_community_name(entry.profile.name)

            pool_stmt = (
                pg_insert(CommunityPool)
                .values(
                    name=name,
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
                    discovered_from_task_id=task.id,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[DiscoveredCommunity.name],
                    set_={
                        "discovered_count": DiscoveredCommunity.discovered_count + mention_count,
                        "last_discovered_at": now,
                        "discovered_from_task_id": task.id,
                        "updated_at": now,
                        "discovered_from_keywords": keywords_payload,
                    },
                )
            )
            await session.execute(stmt)
            upserted_count += 1
        await session.commit()

    return DiscoveredCommunityRecordResult(
        status="completed",
        upserted_count=upserted_count,
    )


__all__ = ["DiscoveredCommunityRecordResult", "record_discovered_communities_for_task"]
