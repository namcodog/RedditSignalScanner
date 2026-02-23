from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.session import SessionFactory
from app.models.hotpost_query import HotpostQuery
from app.models.hotpost_query_evidence_map import HotpostQueryEvidenceMap
from sqlalchemy import text


@pytest.mark.asyncio
async def test_hotpost_query_and_mapping_insert() -> None:
    async with SessionFactory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO evidence_posts (
                    probe_source, source_query, source_query_hash, source_post_id,
                    subreddit, title, summary, score, num_comments, post_created_at, evidence_score
                ) VALUES (
                    :probe_source, :source_query, :source_query_hash, :source_post_id,
                    :subreddit, :title, :summary, :score, :num_comments, :post_created_at, :evidence_score
                )
                RETURNING id
                """
            ),
            {
                "probe_source": "hotpost",
                "source_query": "robot vacuum",
                "source_query_hash": "a" * 64,
                "source_post_id": "abc123",
                "subreddit": "r/test",
                "title": "Test post",
                "summary": None,
                "score": 10,
                "num_comments": 2,
                "post_created_at": datetime.now(timezone.utc),
                "evidence_score": 5,
            },
        )
        evidence_id = result.scalar_one()
        await session.commit()

        query = HotpostQuery(
            query="robot vacuum",
            mode="trending",
            time_filter="week",
            subreddits=["r/test"],
            user_id=None,
            session_id="sess-1",
            ip_hash="hash-1",
            evidence_count=1,
            community_count=1,
            confidence="low",
            from_cache=False,
            latency_ms=123,
            api_calls=3,
        )
        session.add(query)
        await session.commit()

        mapping = HotpostQueryEvidenceMap(
            query_id=query.id,
            evidence_id=evidence_id,
            rank=1,
            signal_score=3.5,
            signals=["broken"],
            top_comment_refs=None,
        )
        session.add(mapping)
        await session.commit()

        assert mapping.id is not None
        assert mapping.query_id == query.id
        assert mapping.evidence_id == evidence_id
