from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.models.semantic_observation import SemanticObservation


def _index_names(table):
    return {index.name: index for index in table.indexes}


def test_community_registry_contract() -> None:
    table = CommunityRegistry.__table__
    indexes = _index_names(table)

    assert "ix_community_registry_key" in indexes
    assert "uq_community_registry_platform_name" in indexes
    assert table.c.community_key.computed is not None
    assert table.c.legacy_pool_id.unique is True


def test_community_domain_membership_contract() -> None:
    table = CommunityDomainMembership.__table__
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ix_community_domain_membership_domain" in indexes
    assert "uq_community_domain_membership_community_domain" in indexes
    assert "ck_community_domain_membership_membership_source_valid" in constraint_names
    assert isinstance(table.c.evidence.type, postgresql.JSONB)


def test_community_governance_decision_contract() -> None:
    table = CommunityGovernanceDecision.__table__
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ix_community_governance_decision_membership_current" in indexes
    assert "ck_community_governance_decision_community_governance_decision_valid" in constraint_names
    assert isinstance(table.c.decided_by.type, postgresql.UUID)


def test_community_runtime_state_contract() -> None:
    table = CommunityRuntimeState.__table__
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert table.primary_key.columns.keys() == ["community_id"]
    assert "ix_community_runtime_state_status" in indexes
    assert "ix_community_runtime_state_last_crawled" in indexes
    assert "ck_community_runtime_state_community_runtime_state_status_valid" in constraint_names
    assert "ck_community_runtime_state_community_runtime_state_priority_range" in constraint_names


def test_semantic_observation_contract() -> None:
    table = SemanticObservation.__table__
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ix_semantic_observation_content" in indexes
    assert "ix_semantic_observation_run_key" in indexes
    assert "ck_semantic_observation_semantic_observation_content_type_valid" in constraint_names
    assert "ck_semantic_observation_semantic_observation_provenance_valid" in constraint_names
    assert isinstance(table.c.evidence.type, postgresql.JSONB)
