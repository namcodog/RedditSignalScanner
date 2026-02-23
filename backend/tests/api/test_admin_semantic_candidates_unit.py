from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.semantic_candidates import (
    ApproveCandidateRequest,
    RejectCandidateRequest,
    approve_semantic_candidate,
    get_semantic_candidate_statistics,
    list_semantic_candidates,
    reject_semantic_candidate,
)
from app.core.security import TokenPayload, hash_password
from app.models.semantic_candidate import SemanticCandidate
from app.models.semantic_term import SemanticTerm
from app.models.user import User
from app.repositories.semantic_candidate_repository import SemanticCandidateRepository
from app.repositories.semantic_term_repository import SemanticTermRepository
from app.services.semantic.audit_logger import SemanticAuditLogger
from app.services.semantic_loader import SemanticLoader
from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_list_and_stats_endpoints_execute(db_session: AsyncSession) -> None:
    payload = TokenPayload(sub=str(uuid.uuid4()))
    # ensure tables are present; rely on migrations
    body = await list_semantic_candidates(
        repo=SemanticCandidateRepository(db_session, SemanticTermRepository(db_session)),
        payload=payload,
    )
    assert body["code"] == 0
    assert isinstance(body["data"]["items"], list)

    stats_body = await get_semantic_candidate_statistics(
        repo=SemanticCandidateRepository(db_session, SemanticTermRepository(db_session)),
        payload=payload,
    )
    assert stats_body["code"] == 0
    assert "total" in stats_body["data"]


@pytest.mark.asyncio
async def test_approve_and_reject_error_branches(db_session: AsyncSession) -> None:
    good_payload = TokenPayload(sub=str(uuid.uuid4()))
    bad_payload = TokenPayload(sub="not-a-uuid")
    repo = SemanticCandidateRepository(db_session, SemanticTermRepository(db_session))
    audit = SemanticAuditLogger(db_session)
    loader = SemanticLoader(SessionFactory)

    with pytest.raises(Exception):
        await approve_semantic_candidate(
            candidate_id=9999,
            body=ApproveCandidateRequest(category="brands", layer="L1"),
            repo=repo,
            audit_logger=audit,
            loader=loader,
            payload=good_payload,
        )

    with pytest.raises(Exception):
        await approve_semantic_candidate(
            candidate_id=1,
            body=ApproveCandidateRequest(category="brands", layer="L1"),
            repo=repo,
            audit_logger=audit,
            loader=loader,
            payload=bad_payload,
        )

    with pytest.raises(Exception):
        await reject_semantic_candidate(
            candidate_id=9999,
            body=RejectCandidateRequest(reason="not relevant"),
            repo=repo,
            audit_logger=audit,
            payload=good_payload,
        )


@pytest.mark.asyncio
async def test_approve_and_reject_success_flow(db_session: AsyncSession) -> None:
    # prepare admin user
    admin_id = uuid.uuid4()
    admin_user = User(
        id=admin_id,
        email="semantic-admin@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(admin_user)
    await db_session.commit()

    payload = TokenPayload(sub=str(admin_id))
    repo = SemanticCandidateRepository(db_session, SemanticTermRepository(db_session))
    audit = SemanticAuditLogger(db_session)
    loader = SemanticLoader(SessionFactory)

    now = datetime.now(timezone.utc)
    candidate = SemanticCandidate(
        term="UnitCoin",
        frequency=3,
        source="posts",
        first_seen_at=now,
        last_seen_at=now,
        status="pending",
    )
    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(candidate)

    approve_body = ApproveCandidateRequest(
        category="brands",
        layer="L1",
        aliases=["unitcoin"],
        weight=1.5,
    )
    resp = await approve_semantic_candidate(
        candidate_id=candidate.id,
        body=approve_body,
        repo=repo,
        audit_logger=audit,
        loader=loader,
        payload=payload,
    )
    assert resp["code"] == 0
    data = resp["data"]
    assert data["canonical"] == "UnitCoin"
    assert "unitcoin" in [a.lower() for a in data["aliases"]]

    term_row = await db_session.execute(
        select(SemanticTerm).where(SemanticTerm.canonical == "UnitCoin")
    )
    term = term_row.scalars().first()
    assert term is not None

    # prepare another candidate for rejection
    candidate2 = SemanticCandidate(
        term="RejectCoin",
        frequency=1,
        source="posts",
        first_seen_at=now,
        last_seen_at=now,
        status="pending",
    )
    db_session.add(candidate2)
    await db_session.commit()
    await db_session.refresh(candidate2)

    reject_body = RejectCandidateRequest(reason="low quality")
    resp_reject = await reject_semantic_candidate(
        candidate_id=candidate2.id,
        body=reject_body,
        repo=repo,
        audit_logger=audit,
        payload=payload,
    )
    assert resp_reject["code"] == 0

