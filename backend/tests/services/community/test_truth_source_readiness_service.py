from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.models.business_category import BusinessCategory
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.models.semantic_observation import SemanticObservation
from app.services.community.truth_source_readiness_service import (
    read_truth_source_readiness_snapshot,
)


async def _ensure_readiness_tables(db_session) -> None:
    async with db_session.bind.begin() as conn:
        await conn.run_sync(BusinessCategory.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityRegistry.__table__.create, checkfirst=True)
        await conn.run_sync(CommunityDomainMembership.__table__.create, checkfirst=True)
        await conn.run_sync(
            CommunityGovernanceDecision.__table__.create,
            checkfirst=True,
        )
        await conn.run_sync(CommunityRuntimeState.__table__.create, checkfirst=True)
        await conn.run_sync(SemanticObservation.__table__.create, checkfirst=True)


async def _cleanup_readiness_rows(db_session, async_truncate_test_tables) -> None:
    await async_truncate_test_tables(
        "community_runtime_state",
        "community_governance_decision",
        "community_domain_membership",
        "community_registry",
    )
    await db_session.execute(
        text(
            """
            DELETE FROM semantic_observation
            WHERE run_key = 'truth-readiness-test'
            """
        )
    )
    await db_session.execute(
        text(
            """
            DELETE FROM posts_raw
            WHERE source = 'readiness-test'
            """
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_read_truth_source_readiness_snapshot_uses_new_truth_tables(
    db_session,
    async_truncate_test_tables,
) -> None:
    await _ensure_readiness_tables(db_session)
    await _cleanup_readiness_rows(db_session, async_truncate_test_tables)
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES ('Tools_EDC', 'Tools EDC')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )
    baseline = await read_truth_source_readiness_snapshot(
        db_session,
        lookback_days=30,
    )

    now = datetime.now(timezone.utc)
    edc = CommunityRegistry(community_name="r/edc", is_enabled=True)
    multitools = CommunityRegistry(community_name="r/multitools", is_enabled=True)
    onebag = CommunityRegistry(community_name="r/onebag", is_enabled=True)
    db_session.add_all([edc, multitools, onebag])
    await db_session.flush()

    memberships = [
        CommunityDomainMembership(
            community_id=edc.id,
            domain_key="Tools_EDC",
            membership_source="reconciled",
            is_primary=True,
            is_current=True,
            evidence={"source": "test"},
        ),
        CommunityDomainMembership(
            community_id=multitools.id,
            domain_key="Tools_EDC",
            membership_source="reconciled",
            is_primary=False,
            is_current=True,
            evidence={"source": "test"},
        ),
    ]
    db_session.add_all(memberships)
    await db_session.flush()

    db_session.add_all(
        [
            CommunityGovernanceDecision(
                membership_id=memberships[0].id,
                decision="approved",
                reason_code="seed",
                evidence={"source": "test"},
                decided_at=now,
                is_current=True,
            ),
            CommunityGovernanceDecision(
                membership_id=memberships[1].id,
                decision="approved",
                reason_code="seed",
                evidence={"source": "test"},
                decided_at=now,
                is_current=True,
            ),
            CommunityRuntimeState(
                community_id=edc.id,
                crawl_status="active",
                is_enabled=True,
                crawl_priority=60,
                sample_posts=12,
                sample_comments=5,
            ),
        ]
    )

    await db_session.commit()

    snapshot = await read_truth_source_readiness_snapshot(
        db_session,
        lookback_days=30,
    )

    assert snapshot.truth_tables_ready is True
    assert snapshot.enabled_registry_count == 3
    assert snapshot.registry_with_current_membership_count == 2
    assert snapshot.approved_registry_count == 2
    assert snapshot.active_runtime_count == 1
    assert snapshot.enabled_registry_missing_membership_count == 1
    assert snapshot.approved_registry_runtime_gap_count == 1
    assert snapshot.membership_coverage_ratio == 0.6667
    assert snapshot.approval_coverage_ratio == 0.6667
    assert snapshot.approved_registry_runtime_gap_ratio == 0.5
    assert snapshot.recent_posts_count == baseline.recent_posts_count
    assert (
        snapshot.recent_posts_with_semantic_count
        == baseline.recent_posts_with_semantic_count
    )
