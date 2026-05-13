"""Add truth-source registry tables for community and semantic layers.

Revision ID: 20260327_000001
Revises: 20260317_000001
Create Date: 2026-03-27 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260327_000001"
down_revision: Union[str, tuple[str, ...], None] = "20260317_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_registry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False, server_default="reddit"),
        sa.Column("community_name", sa.String(length=100), nullable=False),
        sa.Column(
            "community_key",
            sa.String(length=100),
            sa.Computed("lower(regexp_replace(community_name, '^r/', ''))", persisted=True),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=150), nullable=True),
        sa.Column("canonical_url", sa.String(length=255), nullable=True),
        sa.Column(
            "legacy_pool_id",
            sa.Integer(),
            sa.ForeignKey("community_pool.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("source_of_truth", sa.String(length=20), nullable=False, server_default="registry"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_registry")),
    )
    op.create_index(
        "ix_community_registry_key",
        "community_registry",
        ["community_key"],
        unique=False,
    )
    op.create_index(
        "ix_community_registry_enabled",
        "community_registry",
        ["is_enabled"],
        unique=False,
    )
    op.create_index(
        "uq_community_registry_platform_name",
        "community_registry",
        ["platform", "community_name"],
        unique=True,
    )

    op.create_table(
        "community_domain_membership",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "community_id",
            sa.Integer(),
            sa.ForeignKey("community_registry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "domain_key",
            sa.String(length=50),
            sa.ForeignKey("business_categories.key", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("membership_source", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "membership_source IN ('seed','manual','reconciled','heuristic','llm')",
            name=op.f("ck_community_domain_membership_membership_source_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_domain_membership")),
    )
    op.create_index(
        "ix_community_domain_membership_domain",
        "community_domain_membership",
        ["domain_key"],
        unique=False,
    )
    op.create_index(
        "uq_community_domain_membership_community_domain",
        "community_domain_membership",
        ["community_id", "domain_key"],
        unique=True,
    )
    op.create_index(
        "ux_community_domain_membership_primary_current",
        "community_domain_membership",
        ["community_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true AND is_current = true"),
    )

    op.create_table(
        "community_governance_decision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "membership_id",
            sa.Integer(),
            sa.ForeignKey("community_domain_membership.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "decided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('approved','review','blocked','archived')",
            name=op.f("ck_community_governance_decision_community_governance_decision_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_governance_decision")),
    )
    op.create_index(
        "ix_community_governance_decision_membership_current",
        "community_governance_decision",
        ["membership_id", "is_current"],
        unique=False,
    )
    op.create_index(
        "ux_community_governance_decision_current",
        "community_governance_decision",
        ["membership_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    op.create_table(
        "community_runtime_state",
        sa.Column(
            "community_id",
            sa.Integer(),
            sa.ForeignKey("community_registry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("crawl_status", sa.String(length=20), nullable=False),
        sa.Column("crawl_priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("legacy_cache_name", sa.String(length=100), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=True),
        sa.Column("sample_posts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_post_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backfill_floor", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "runtime_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "crawl_status IN ('active','paused','blocked','needs_backfill')",
            name=op.f("ck_community_runtime_state_community_runtime_state_status_valid"),
        ),
        sa.CheckConstraint(
            "crawl_priority BETWEEN 1 AND 100",
            name=op.f("ck_community_runtime_state_community_runtime_state_priority_range"),
        ),
        sa.PrimaryKeyConstraint("community_id", name=op.f("pk_community_runtime_state")),
    )
    op.create_index(
        "ix_community_runtime_state_status",
        "community_runtime_state",
        ["crawl_status"],
        unique=False,
    )
    op.create_index(
        "ix_community_runtime_state_last_crawled",
        "community_runtime_state",
        ["last_crawled_at"],
        unique=False,
    )

    op.create_table(
        "semantic_observation",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.BigInteger(), nullable=False),
        sa.Column("observation_type", sa.String(length=32), nullable=False),
        sa.Column(
            "term_id",
            sa.BigInteger(),
            sa.ForeignKey("semantic_terms.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "concept_id",
            sa.Integer(),
            sa.ForeignKey("semantic_concepts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label_key", sa.String(length=128), nullable=True),
        sa.Column("label_value", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("provenance", sa.String(length=20), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=True),
        sa.Column("source_model", sa.String(length=128), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semantic_observation")),
        sa.CheckConstraint(
            "content_type IN ('post','comment')",
            name=op.f("ck_semantic_observation_semantic_observation_content_type_valid"),
        ),
        sa.CheckConstraint(
            "provenance IN ('rule','llm','import','reconciled')",
            name=op.f("ck_semantic_observation_semantic_observation_provenance_valid"),
        ),
    )
    op.create_index(
        "ix_semantic_observation_content",
        "semantic_observation",
        ["content_type", "content_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_observation_observation_type",
        "semantic_observation",
        ["observation_type"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_observation_term_id",
        "semantic_observation",
        ["term_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_observation_concept_id",
        "semantic_observation",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_observation_run_key",
        "semantic_observation",
        ["run_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_observation_run_key", table_name="semantic_observation")
    op.drop_index("ix_semantic_observation_concept_id", table_name="semantic_observation")
    op.drop_index("ix_semantic_observation_term_id", table_name="semantic_observation")
    op.drop_index("ix_semantic_observation_observation_type", table_name="semantic_observation")
    op.drop_index("ix_semantic_observation_content", table_name="semantic_observation")
    op.drop_table("semantic_observation")

    op.drop_index("ix_community_runtime_state_last_crawled", table_name="community_runtime_state")
    op.drop_index("ix_community_runtime_state_status", table_name="community_runtime_state")
    op.drop_table("community_runtime_state")

    op.drop_index("ux_community_governance_decision_current", table_name="community_governance_decision")
    op.drop_index(
        "ix_community_governance_decision_membership_current",
        table_name="community_governance_decision",
    )
    op.drop_table("community_governance_decision")

    op.drop_index(
        "ux_community_domain_membership_primary_current",
        table_name="community_domain_membership",
    )
    op.drop_index(
        "uq_community_domain_membership_community_domain",
        table_name="community_domain_membership",
    )
    op.drop_index("ix_community_domain_membership_domain", table_name="community_domain_membership")
    op.drop_table("community_domain_membership")

    op.drop_index("uq_community_registry_platform_name", table_name="community_registry")
    op.drop_index("ix_community_registry_enabled", table_name="community_registry")
    op.drop_index("ix_community_registry_key", table_name="community_registry")
    op.drop_table("community_registry")
