from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.semantic_candidate import SemanticCandidate
from app.models.semantic_term import SemanticTerm
from app.models.user import User
from app.repositories.semantic_candidate_repository import SemanticCandidateRepository
from app.repositories.semantic_term_repository import SemanticTermRepository


@pytest.mark.asyncio
async def test_semantic_term_repository_crud_and_search() -> None:
    async with SessionFactory() as session:
        # Alembic 迁移已在测试启动时应用，此处不再显式建表

        repo = SemanticTermRepository(session)
        term = SemanticTerm(
            canonical="btc_repo",
            aliases=["bitcoin", "xbt"],
            category="brands",
            layer="L1",
            precision_tag="exact",
            weight=1.0,
            polarity="positive",
        )
        created = await repo.create(term)
        assert created.id is not None

        fetched_all = await repo.get_all()
        assert any(t.canonical == "btc_repo" for t in fetched_all)

        fetched_cat = await repo.get_by_category("brands")
        assert any(t.canonical == "btc_repo" for t in fetched_cat)

        updated = await repo.update(
            created.id,
            {"lifecycle": "candidate"},
        )
        assert updated.lifecycle == "candidate"

        results = await repo.search("btc")
        assert any(t.canonical == "btc_repo" for t in results)

        await repo.delete(created.id)
        remaining = await session.execute(
            select(SemanticTerm).where(SemanticTerm.id == created.id)
        )
        assert remaining.scalars().first() is None


@pytest.mark.asyncio
async def test_semantic_candidate_repository_upsert_and_approve() -> None:
    async with SessionFactory() as session:
        # 依赖迁移创建的表结构

        user = User(
            email="candidate-review@example.com",
            password_hash=hash_password("SecurePass123!"),
        )
        session.add(user)
        await session.flush()

        term_repo = SemanticTermRepository(session)
        cand_repo = SemanticCandidateRepository(session, term_repo)

        # upsert: insert
        candidate = await cand_repo.upsert("newcoin", "posts")
        assert candidate.frequency == 1
        # 新口径（第9）：candidate 写入 semantic_rules（is_active=false）
        row = await session.execute(
            select(SemanticCandidate).where(SemanticCandidate.id == candidate.id)
        )
        assert row.scalars().first() is not None

        # upsert: update
        candidate2 = await cand_repo.upsert("newcoin", "posts")
        assert candidate2.id == candidate.id
        assert candidate2.frequency == 2

        pending = await cand_repo.get_pending(limit=10)
        assert any(c.term == "newcoin" for c in pending)

        # approve should create term and delete candidate
        approved_term = await cand_repo.approve(
            candidate.id, category="brands", layer="L2", operator_id=user.id
        )
        assert approved_term.canonical == "newcoin"

        # 新口径（第9）：approved 也必须同步到 semantic_rules（is_active=true）
        from sqlalchemy import text as sqltext

        res = await session.execute(
            sqltext(
                """
                SELECT r.is_active
                FROM semantic_rules r
                JOIN semantic_concepts c ON c.id = r.concept_id
                WHERE c.code = 'candidate_terms'
                  AND r.term = :term
                ORDER BY r.updated_at DESC
                LIMIT 1
                """
            ),
            {"term": "newcoin"},
        )
        is_active = res.scalar_one_or_none()
        assert is_active is True

        remaining = await session.execute(
            select(SemanticCandidate).where(SemanticCandidate.id == candidate.id)
        )
        assert remaining.scalars().first() is None


@pytest.mark.asyncio
async def test_semantic_candidate_repository_reject_and_statistics() -> None:
    async with SessionFactory() as session:
        # 依赖迁移创建的表结构

        user = User(
            email="candidate-reject@example.com",
            password_hash=hash_password("SecurePass123!"),
        )
        session.add(user)
        await session.flush()

        term_repo = SemanticTermRepository(session)
        cand_repo = SemanticCandidateRepository(session, term_repo)

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                SemanticCandidate(
                    term="foo",
                    frequency=5,
                    source="posts",
                    first_seen_at=now - timedelta(days=1),
                    last_seen_at=now,
                ),
                SemanticCandidate(
                    term="bar",
                    frequency=10,
                    source="comments",
                    first_seen_at=now - timedelta(days=2),
                    last_seen_at=now,
                ),
            ]
        )
        await session.commit()

        pending = await cand_repo.get_pending(limit=10)
        assert [c.term for c in pending] == ["bar", "foo"]

        await cand_repo.reject(
            pending[0].id, reason="not relevant", operator_id=user.id
        )
        stats = await cand_repo.get_statistics()
        assert stats["total"] >= 2
        assert stats["pending"] >= 1
