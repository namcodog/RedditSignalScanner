from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_tier_suggestion_table_indexes_and_defaults() -> None:
    from app.models.tier_suggestion import TierSuggestion

    table = TierSuggestion.__table__
    indexes = {idx.name for idx in table.indexes}

    # Naming follows global naming_convention: ix_<table>_<first_column>
    assert "ix_tier_suggestions_community_name" in indexes
    assert "ix_tier_suggestions_status" in indexes

    reasons_col = table.c.reasons
    metrics_col = table.c.metrics
    status_col = table.c.status

    assert isinstance(reasons_col.type, postgresql.JSONB)
    assert isinstance(metrics_col.type, postgresql.JSONB)
    assert status_col.default is not None


@pytest.mark.asyncio
async def test_tier_suggestion_insert_roundtrip() -> None:
    from app.models.tier_suggestion import TierSuggestion

    async with SessionFactory() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: TierSuggestion.__table__.create(
                    sync_conn,
                    checkfirst=True,
                )
            )

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        sugg = TierSuggestion(
            community_name="r/example",
            current_tier="T2",
            suggested_tier="T1",
            confidence=0.9,
            reasons=["high activity", "high pain density"],
            metrics={"posts_per_day": 120.0},
            priority_score=10,
            expires_at=expires_at,
        )
        session.add(sugg)
        await session.commit()
        await session.refresh(sugg)

        assert sugg.id is not None
        assert sugg.status == "pending"
        assert sugg.community_name == "r/example"


@pytest.mark.asyncio
async def test_tier_audit_log_table_indexes_and_defaults() -> None:
    from app.models.tier_audit_log import TierAuditLog

    table = TierAuditLog.__table__
    indexes = {idx.name for idx in table.indexes}

    assert "ix_tier_audit_logs_community_name" in indexes
    assert "ix_tier_audit_logs_action" in indexes
    assert "ix_tier_audit_logs_is_rolled_back" in indexes

    before_col = table.c.snapshot_before
    after_col = table.c.snapshot_after
    rolled_col = table.c.is_rolled_back

    assert isinstance(before_col.type, postgresql.JSONB)
    assert isinstance(after_col.type, postgresql.JSONB)
    assert rolled_col.default is not None


@pytest.mark.asyncio
async def test_tier_audit_log_insert_and_flags(db_session) -> None:
    from app.models.tier_audit_log import TierAuditLog

    async with db_session.bind.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: TierAuditLog.__table__.create(
                sync_conn,
                checkfirst=True,
            )
        )

    log = TierAuditLog(
        community_name="r/example",
        action="tier_change",
        field_changed="tier",
        from_value="T2",
        to_value="T1",
        changed_by="admin@example.com",
        change_source="manual",
        reason="manual upgrade in test",
        snapshot_before={"tier": "T2"},
        snapshot_after={"tier": "T1"},
        suggestion_id=None,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.is_rolled_back is False


@pytest.mark.asyncio
async def test_community_pool_health_fields_defaults(db_session) -> None:
    from app.models.community_pool import CommunityPool

    async with db_session.bind.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: CommunityPool.__table__.create(
                sync_conn,
                checkfirst=True,
            )
        )

    pool = CommunityPool(
        name="r/example_health",
        tier="T2",
        categories={"source": "test"},
        description_keywords={"keywords": ["k1"]},
        daily_posts=10,
        avg_comment_length=20,
        quality_score=0.5,
        priority="medium",
        user_feedback_count=0,
        discovered_count=0,
        is_active=True,
    )
    db_session.add(pool)
    await db_session.commit()
    await db_session.refresh(pool)

    assert pool.health_status == "unknown"
    assert pool.auto_tier_enabled is True
    assert pool.last_evaluated_at is None
