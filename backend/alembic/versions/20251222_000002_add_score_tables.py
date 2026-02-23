"""Add score tables for post/comment scoring."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20251222_000002"
down_revision: str | None = "20251222_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
        return result.scalar() is not None
    except Exception:
        return False


def _index_exists(name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
        return result.scalar() is not None
    except Exception:
        return False


def _dedupe_latest(table_name: str, id_column: str, content_column: str) -> None:
    op.execute(
        f"""
        WITH ranked AS (
            SELECT {id_column} AS id,
                   ROW_NUMBER() OVER (
                       PARTITION BY {content_column}
                       ORDER BY is_latest DESC, scored_at DESC NULLS LAST, {id_column} DESC
                   ) AS rn
            FROM {table_name}
            WHERE is_latest = TRUE
        )
        UPDATE {table_name} t
        SET is_latest = FALSE
        FROM ranked r
        WHERE t.{id_column} = r.id AND r.rn > 1;
        """
    )


def upgrade() -> None:
    if not _table_exists("post_scores"):
        op.create_table(
            "post_scores",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "post_id",
                sa.BigInteger(),
                sa.ForeignKey("posts_raw.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("llm_version", sa.String(length=50), nullable=False),
            sa.Column("rule_version", sa.String(length=50), nullable=False),
            sa.Column(
                "scored_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("is_latest", sa.Boolean(), server_default=sa.text("TRUE")),
            sa.Column("value_score", sa.Numeric(4, 2)),
            sa.Column("opportunity_score", sa.Numeric(4, 2)),
            sa.Column("business_pool", sa.String(length=20)),
            sa.Column("sentiment", sa.Numeric(4, 3)),
            sa.Column("purchase_intent_score", sa.Numeric(4, 2)),
            sa.Column(
                "tags_analysis",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "entities_extracted",
                postgresql.JSONB(),
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "calculation_log",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.CheckConstraint(
                "business_pool IN ('core', 'lab', 'noise')",
                name="ck_post_scores_business_pool",
            ),
        )

    if not _table_exists("comment_scores"):
        op.create_table(
            "comment_scores",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "comment_id",
                sa.BigInteger(),
                sa.ForeignKey("comments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("llm_version", sa.String(length=50), nullable=False),
            sa.Column("rule_version", sa.String(length=50), nullable=False),
            sa.Column(
                "scored_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("is_latest", sa.Boolean(), server_default=sa.text("TRUE")),
            sa.Column("value_score", sa.Numeric(4, 2)),
            sa.Column("opportunity_score", sa.Numeric(4, 2)),
            sa.Column("business_pool", sa.String(length=20)),
            sa.Column("sentiment", sa.Numeric(4, 3)),
            sa.Column("purchase_intent_score", sa.Numeric(4, 2)),
            sa.Column(
                "tags_analysis",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "entities_extracted",
                postgresql.JSONB(),
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "calculation_log",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.CheckConstraint(
                "business_pool IN ('core', 'lab', 'noise')",
                name="ck_comment_scores_business_pool",
            ),
        )

    if _table_exists("post_scores"):
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_post_scores_post_latest
            ON post_scores (post_id) WHERE is_latest = TRUE
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_post_scores_rule_version ON post_scores (rule_version)"
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_post_scores_pool
            ON post_scores (business_pool) WHERE is_latest = TRUE
            """
        )
        if not _index_exists("ux_post_scores_latest"):
            _dedupe_latest("post_scores", "id", "post_id")
            op.execute(
                """
                CREATE UNIQUE INDEX ux_post_scores_latest
                ON post_scores (post_id) WHERE is_latest = TRUE
                """
            )

    if _table_exists("comment_scores"):
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_comment_scores_comment_latest
            ON comment_scores (comment_id) WHERE is_latest = TRUE
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_comment_scores_rule_version ON comment_scores (rule_version)"
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_comment_scores_pool
            ON comment_scores (business_pool) WHERE is_latest = TRUE
            """
        )
        if not _index_exists("ux_comment_scores_latest"):
            _dedupe_latest("comment_scores", "id", "comment_id")
            op.execute(
                """
                CREATE UNIQUE INDEX ux_comment_scores_latest
                ON comment_scores (comment_id) WHERE is_latest = TRUE
                """
            )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_comment_scores_latest")
    op.execute("DROP INDEX IF EXISTS ux_post_scores_latest")
    op.execute("DROP INDEX IF EXISTS idx_comment_scores_pool")
    op.execute("DROP INDEX IF EXISTS idx_comment_scores_rule_version")
    op.execute("DROP INDEX IF EXISTS idx_comment_scores_comment_latest")
    op.execute("DROP INDEX IF EXISTS idx_post_scores_pool")
    op.execute("DROP INDEX IF EXISTS idx_post_scores_rule_version")
    op.execute("DROP INDEX IF EXISTS idx_post_scores_post_latest")

    if _table_exists("comment_scores"):
        op.drop_table("comment_scores")
    if _table_exists("post_scores"):
        op.drop_table("post_scores")
