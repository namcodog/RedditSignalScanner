from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovered_community import DiscoveredCommunity
from app.models.evidence_post import EvidencePost
from app.models.hotpost_query import HotpostQuery
from app.models.hotpost_query_evidence_map import HotpostQueryEvidenceMap
from app.utils.subreddit import normalize_subreddit_name


def normalize_query(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def build_query_hash(text: str) -> str:
    source_query = normalize_query(text)
    return hashlib.sha256(source_query.encode("utf-8")).hexdigest()


async def create_hotpost_query(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    query: str,
    mode: str,
    time_filter: str,
    subreddits: list[str] | None,
    user_id: uuid.UUID | None,
    session_id: str | None,
    ip_hash: str | None,
    evidence_count: int,
    community_count: int,
    confidence: str,
    from_cache: bool,
    latency_ms: int | None,
    api_calls: int | None,
) -> HotpostQuery:
    record = HotpostQuery(
        id=query_id,
        query=query,
        mode=mode,
        time_filter=time_filter,
        subreddits=subreddits,
        user_id=user_id,
        session_id=session_id,
        ip_hash=ip_hash,
        evidence_count=evidence_count,
        community_count=community_count,
        confidence=confidence,
        from_cache=from_cache,
        latency_ms=latency_ms,
        api_calls=api_calls,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.commit()
    return record


async def update_hotpost_query(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    evidence_count: int,
    community_count: int,
    confidence: str,
    from_cache: bool,
    latency_ms: int | None,
    api_calls: int | None,
    subreddits: list[str] | None = None,
) -> None:
    result = await db.execute(
        select(HotpostQuery).where(HotpostQuery.id == query_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return
    record.evidence_count = evidence_count
    record.community_count = community_count
    record.confidence = confidence
    record.from_cache = from_cache
    record.latency_ms = latency_ms
    record.api_calls = api_calls
    if subreddits is not None:
        record.subreddits = subreddits
    await db.commit()


async def upsert_evidence_post(
    db: AsyncSession,
    *,
    probe_source: str,
    source_query: str,
    source_post_id: str,
    subreddit: str,
    title: str,
    summary: str | None,
    score: int,
    num_comments: int,
    post_created_at: datetime | None,
    evidence_score: int,
) -> EvidencePost:
    source_query_hash = build_query_hash(source_query)
    result = await db.execute(
        select(EvidencePost).where(
            EvidencePost.probe_source == probe_source,
            EvidencePost.source_query_hash == source_query_hash,
            EvidencePost.source_post_id == source_post_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    evidence = EvidencePost(
        probe_source=probe_source,
        source_query=source_query,
        source_query_hash=source_query_hash,
        source_post_id=source_post_id,
        subreddit=subreddit,
        title=title,
        summary=summary,
        score=score,
        num_comments=num_comments,
        post_created_at=post_created_at,
        evidence_score=evidence_score,
    )
    db.add(evidence)
    await db.commit()
    return evidence


async def insert_query_evidence_map(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    evidence_id: int,
    rank: int | None,
    signal_score: float | None,
    signals: list[str] | None,
    top_comment_refs: list[dict[str, Any]] | None,
) -> HotpostQueryEvidenceMap:
    mapping = HotpostQueryEvidenceMap(
        query_id=query_id,
        evidence_id=evidence_id,
        rank=rank,
        signal_score=signal_score,
        signals=signals,
        top_comment_refs=top_comment_refs,
        created_at=datetime.now(timezone.utc),
    )
    db.add(mapping)
    await db.commit()
    return mapping


async def maybe_discover_community(
    db: AsyncSession,
    *,
    subreddit: str,
    evidence_count: int,
    query: str | None,
    keywords: list[str],
    task_id: uuid.UUID | None = None,
) -> None:
    canonical = normalize_subreddit_name(subreddit)
    if not canonical:
        return
    if evidence_count < 5:
        return

    result = await db.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == canonical)
    )
    if result.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)
    record = DiscoveredCommunity(
        name=canonical,
        discovered_from_keywords={
            "source": "hotpost",
            "query": query,
            "keywords": keywords,
        },
        discovered_count=evidence_count,
        first_discovered_at=now,
        last_discovered_at=now,
        status="pending",
        discovered_from_task_id=task_id,
    )
    db.add(record)
    await db.commit()


__all__ = [
    "normalize_query",
    "build_query_hash",
    "create_hotpost_query",
    "update_hotpost_query",
    "upsert_evidence_post",
    "insert_query_evidence_map",
    "maybe_discover_community",
]
