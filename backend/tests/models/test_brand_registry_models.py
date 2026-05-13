from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql

from app.models.brand_registry import BrandMention, BrandRegistry


def _index_names(table: Table) -> set[str]:
    return {index.name or "" for index in table.indexes}


def test_brand_registry_contract() -> None:
    table = cast(Table, BrandRegistry.__table__)
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "uq_brand_registry_brand_key" in constraint_names
    assert "ix_brand_registry_status" in indexes
    assert "ix_brand_registry_active" in indexes
    assert isinstance(table.c.domains.type, postgresql.ARRAY)
    assert isinstance(table.c.risk_flags.type, postgresql.ARRAY)
    assert isinstance(table.c.source_payload.type, postgresql.JSONB)


def test_brand_mentions_contract() -> None:
    table = cast(Table, BrandMention.__table__)
    indexes = _index_names(table)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "uq_brand_mentions_mention_key" in constraint_names
    assert "ix_brand_mentions_brand_source" in indexes
    assert "ix_brand_mentions_observed_at" in indexes
    assert isinstance(table.c.evidence_payload.type, postgresql.JSONB)
