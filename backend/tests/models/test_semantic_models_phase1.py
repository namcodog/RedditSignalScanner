from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.user import User


@pytest.mark.asyncio
async def test_semantic_term_table_indexes_and_defaults() -> None:
    from app.models.semantic_term import SemanticTerm

    table = SemanticTerm.__table__
    indexes = {idx.name: idx for idx in table.indexes}

    assert "ix_semantic_terms_canonical" in indexes
    assert indexes["ix_semantic_terms_canonical"].unique is True
    assert "ix_semantic_terms_category_layer" in indexes
    assert "ix_semantic_terms_lifecycle" in indexes

    lifecycle_col = table.c.lifecycle
    assert lifecycle_col.default is not None


@pytest.mark.asyncio
async def test_semantic_term_insert_roundtrip() -> None:
    from app.models.semantic_term import SemanticTerm

    async with SessionFactory() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: SemanticTerm.__table__.create(
                    sync_conn, checkfirst=True
                )
            )

        canonical = f"btc_{uuid.uuid4().hex[:8]}"
        term = SemanticTerm(
            canonical=canonical,
            aliases=["bitcoin", "xbt"],
            category="asset",
            layer="L1",
            precision_tag="exact",
            weight=1.0,
            polarity="positive",
        )
        session.add(term)
        await session.commit()
        await session.refresh(term)

        assert term.id is not None
        assert term.canonical == canonical
        assert term.lifecycle == "approved"


@pytest.mark.asyncio
async def test_semantic_candidate_indexes_and_status_default() -> None:
    from app.models.semantic_candidate import SemanticCandidate

    table = SemanticCandidate.__table__
    indexes = {idx.name: idx for idx in table.indexes}

    assert "ix_semantic_candidates_status" in indexes
    assert "ix_semantic_candidates_frequency" in indexes
    assert "ix_semantic_candidates_first_seen_at" in indexes

    status_col = table.c.status
    assert status_col.default is not None


@pytest.mark.asyncio
async def test_semantic_candidate_review_fields_and_fk() -> None:
    from app.models.semantic_candidate import SemanticCandidate

    async with SessionFactory() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: SemanticCandidate.__table__.create(
                    sync_conn, checkfirst=True
                )
            )

        user = User(
            email="semantic-review@example.com",
            password_hash=hash_password("SecurePass123!"),
        )
        session.add(user)
        await session.flush()

        candidate = SemanticCandidate(
            term="altcoin",
            frequency=10,
            source="posts",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            status="pending",
            reviewed_by=user.id,
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        assert candidate.reviewed_by == user.id


@pytest.mark.asyncio
async def test_semantic_audit_log_indexes_and_types() -> None:
    from app.models.semantic_audit_log import SemanticAuditLog

    table = SemanticAuditLog.__table__
    indexes = {idx.name: idx for idx in table.indexes}

    assert "ix_semantic_audit_logs_entity" in indexes
    assert "ix_semantic_audit_logs_created_at" in indexes
    assert "ix_semantic_audit_logs_operator_id" in indexes
    changes_col = table.c.changes
    assert isinstance(changes_col.type, postgresql.JSONB)


@pytest.mark.asyncio
async def test_semantic_audit_log_insert_and_immutable_behavior(db_session) -> None:
    from app.models.semantic_audit_log import SemanticAuditLog

    async with db_session.bind.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SemanticAuditLog.__table__.create(
                sync_conn, checkfirst=True
            )
        )

    log = SemanticAuditLog(
        action="create",
        entity_type="semantic_term",
        entity_id=1,
        changes={"before": None, "after": {"canonical": "btc"}},
        operator_id=None,
        operator_ip="127.0.0.1",
        reason="initial import",
    )
    db_session.add(log)
    await db_session.commit()

    await db_session.refresh(log)
    assert log.id is not None
    assert log.changes["after"]["canonical"] == "btc"
