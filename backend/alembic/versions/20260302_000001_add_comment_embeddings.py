"""add comment embeddings table

Revision ID: 20260302_000001
Revises: 20260202_000001
Create Date: 2026-03-02
"""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260302_000001"
down_revision: str | None = "20260202_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS comment_embeddings (
            comment_id BIGINT NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            embedding vector(1024) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            source_model VARCHAR(50),
            feature_version INTEGER,
            CONSTRAINT pk_comment_embeddings PRIMARY KEY (comment_id, model_version),
            CONSTRAINT fk_comment_embeddings_comment
                FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_comment_embeddings_hnsw
        ON comment_embeddings USING hnsw (embedding vector_cosine_ops)
        WITH (m='16', ef_construction='128');
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_comment_embeddings_comment_id
        ON comment_embeddings (comment_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_comment_embeddings_hnsw;")
    op.execute("DROP INDEX IF EXISTS idx_comment_embeddings_comment_id;")
    op.execute("DROP TABLE IF EXISTS comment_embeddings;")
