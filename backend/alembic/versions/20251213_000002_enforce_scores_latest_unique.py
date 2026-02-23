"""enforce uniqueness for latest scores

Revision ID: 20251213_000002
Revises: 20251209_000001
Create Date: 2025-12-13 00:00:00.000000

Goal: ensure *_scores tables have at most one is_latest record per content.
This migration is defensive: it first demotes duplicate latest rows to
is_latest = false (keeping the newest scored_at), then adds partial unique
indexes on (post_id|comment_id) where is_latest = true.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251213_000002"
down_revision = "20251209_000001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": table_name})
        return result.scalar() is not None
    except Exception:
        return False


def _dedupe_latest(table_name: str, id_column: str, content_column: str) -> None:
    """Demote duplicate latest rows, keeping the most recent scored_at.

    Postgres will refuse a partial unique index if duplicates exist; this
    helper makes the index creation safe by flipping older duplicates to
    is_latest = false. Ordering prioritises is_latest DESC (if any false
    sneaked in), then scored_at DESC, then id as a stable tie-breaker.
    """

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
    # 1) Demote duplicates to make room for partial unique indexes
    if _table_exists("post_scores"):
        _dedupe_latest("post_scores", "id", "post_id")
        op.create_index(
            "ux_post_scores_latest",
            "post_scores",
            ["post_id"],
            unique=True,
            postgresql_where=sa.text("is_latest = true"),
        )

    if _table_exists("comment_scores"):
        _dedupe_latest("comment_scores", "id", "comment_id")
        op.create_index(
            "ux_comment_scores_latest",
            "comment_scores",
            ["comment_id"],
            unique=True,
            postgresql_where=sa.text("is_latest = true"),
        )


def downgrade() -> None:
    # Drop partial unique indexes; we do not attempt to restore demoted rows
    op.execute("DROP INDEX IF EXISTS ux_comment_scores_latest")
    op.execute("DROP INDEX IF EXISTS ux_post_scores_latest")
