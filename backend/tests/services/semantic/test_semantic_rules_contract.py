from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.community_discovery import CommunityDiscoveryService
from app.services.infrastructure.reddit_client import RedditAPIClient


@pytest.mark.asyncio
async def test_fetch_pain_keywords_reads_semantic_rules_term_column() -> None:
    async with SessionFactory() as session:
        concept_id = int(uuid.uuid4().int % 1_000_000_000)
        await session.execute(
            text(
                """
                INSERT INTO semantic_concepts (id, code, name, domain, is_active)
                VALUES (:id, :code, :name, :domain, true)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": concept_id,
                "code": f"c{concept_id}",
                "name": "test",
                "domain": "general",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO semantic_rules (concept_id, term, rule_type, weight, is_active)
                VALUES (:concept_id, :term, :rule_type, 10.0, true)
                """
            ),
            {
                "concept_id": concept_id,
                "term": "refund denied",
                "rule_type": "pain_keywords",
            },
        )
        await session.commit()

        reddit = RedditAPIClient("dummy", "dummy", "dummy-agent")
        service = CommunityDiscoveryService(session, reddit)
        keywords = await service._fetch_pain_keywords_from_db(limit=5)
        assert "refund denied" in keywords

