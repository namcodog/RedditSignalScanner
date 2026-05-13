"""add brand registry tables"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260512_000001"
down_revision = "20260513_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("brand_key", sa.String(length=160), nullable=False),
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("source_lifecycle", sa.String(length=40), nullable=False),
        sa.Column(
            "domains",
            postgresql.ARRAY(sa.String(length=80)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "interest_tags",
            postgresql.ARRAY(sa.String(length=80)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.String(length=200)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "risk_flags",
            postgresql.ARRAY(sa.String(length=80)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "source_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("brand_key", name="uq_brand_registry_brand_key"),
    )
    op.create_index("ix_brand_registry_status", "brand_registry", ["review_status"])
    op.create_index("ix_brand_registry_active", "brand_registry", ["is_active"])

    op.create_table(
        "brand_mentions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "brand_id",
            sa.Integer(),
            sa.ForeignKey("brand_registry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mention_key", sa.String(length=64), nullable=False),
        sa.Column("brand_key", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=160), nullable=False),
        sa.Column("community", sa.String(length=120), nullable=True),
        sa.Column("source_field", sa.String(length=40), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permalink", sa.Text(), nullable=True),
        sa.Column(
            "evidence_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("mention_key", name="uq_brand_mentions_mention_key"),
    )
    op.create_index(
        "ix_brand_mentions_brand_source", "brand_mentions", ["brand_id", "source"]
    )
    op.create_index("ix_brand_mentions_observed_at", "brand_mentions", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_brand_mentions_observed_at", table_name="brand_mentions")
    op.drop_index("ix_brand_mentions_brand_source", table_name="brand_mentions")
    op.drop_table("brand_mentions")
    op.drop_index("ix_brand_registry_active", table_name="brand_registry")
    op.drop_index("ix_brand_registry_status", table_name="brand_registry")
    op.drop_table("brand_registry")
