"""Create score read views and business-scope comments view.

Revision ID: 20251217_000005
Revises: 20251217_000004
Create Date: 2025-12-17

Why:
- The project already relies on `post_scores_latest_v` / `comment_scores_latest_v` as the
  safe read entry for rulebook_v1 + is_latest, but those views were only provided as
  ad-hoc SQL scripts and not guaranteed by Alembic.
- Downstream “正常业务口径”需要稳定：读 comments 时默认只看 core+lab，后续清理 noise
  不应悄悄改变报表/统计含义。

This migration is read-only to existing business data (creates/updates views only).
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251217_000005"
down_revision: str | None = "20251217_000004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _relation_exists(name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
        return result.scalar() is not None
    except Exception:
        return False


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=:table AND column_name=:column
                LIMIT 1
                """
            ),
            {"table": table, "column": column},
        )
        return result.first() is not None
    except Exception:
        return False


def upgrade() -> None:
    # 1) Ensure latest score read views exist (rulebook_v1 + is_latest)
    if _relation_exists("post_scores"):
        op.execute(
            """
            CREATE OR REPLACE VIEW post_scores_latest_v AS
            -- NOTE: Postgres cannot drop/reorder columns via CREATE OR REPLACE VIEW.
            -- Keep column set compatible with existing deployments (id + is_latest included).
            SELECT id,
                   post_id,
                   llm_version,
                   rule_version,
                   scored_at,
                   is_latest,
                   value_score,
                   opportunity_score,
                   business_pool,
                   sentiment,
                   purchase_intent_score,
                   tags_analysis,
                   entities_extracted,
                   calculation_log
            FROM post_scores
            WHERE is_latest = true
              AND rule_version = 'rulebook_v1';
            """
        )
    else:
        op.execute(
            """
            CREATE OR REPLACE VIEW post_scores_latest_v AS
            SELECT
                NULL::bigint AS id,
                NULL::bigint AS post_id,
                NULL::text AS llm_version,
                NULL::text AS rule_version,
                NULL::timestamptz AS scored_at,
                NULL::boolean AS is_latest,
                NULL::double precision AS value_score,
                NULL::double precision AS opportunity_score,
                NULL::text AS business_pool,
                NULL::text AS sentiment,
                NULL::double precision AS purchase_intent_score,
                '{}'::jsonb AS tags_analysis,
                '[]'::jsonb AS entities_extracted,
                '{}'::jsonb AS calculation_log
            WHERE FALSE;
            """
        )

    if _relation_exists("comment_scores"):
        op.execute(
            """
            CREATE OR REPLACE VIEW comment_scores_latest_v AS
            SELECT comment_id,
                   rule_version,
                   llm_version,
                   value_score,
                   opportunity_score,
                   business_pool,
                   sentiment,
                   purchase_intent_score,
                   tags_analysis,
                   entities_extracted,
                   calculation_log,
                   scored_at
            FROM comment_scores
            WHERE is_latest = true
              AND rule_version = 'rulebook_v1';
            """
        )
    else:
        op.execute(
            """
            CREATE OR REPLACE VIEW comment_scores_latest_v AS
            SELECT
                NULL::bigint AS comment_id,
                NULL::text AS rule_version,
                NULL::text AS llm_version,
                NULL::double precision AS value_score,
                NULL::double precision AS opportunity_score,
                NULL::text AS business_pool,
                NULL::text AS sentiment,
                NULL::double precision AS purchase_intent_score,
                '{}'::jsonb AS tags_analysis,
                '[]'::jsonb AS entities_extracted,
                '{}'::jsonb AS calculation_log,
                NULL::timestamptz AS scored_at
            WHERE FALSE;
            """
        )

    # 2) Refresh semantic task view now that post_scores_latest_v is guaranteed.
    # Keep it compilable even if downstream tables are partial in some envs.
    if (
        _relation_exists("comments")
        and _relation_exists("post_scores_latest_v")
        and _column_exists("comments", "post_id")
    ):
        op.execute(
            """
            CREATE OR REPLACE VIEW v_comment_semantic_tasks AS
            SELECT
                c.id AS comment_id,
                c.reddit_comment_id,
                c.source_post_id,
                c.subreddit,
                LEFT(c.body, 1200) AS text_for_llm,
                c.score,
                c.depth,
                c.created_utc,
                c.fetched_at,
                c.lang,
                c.source_track,
                c.first_seen_at
            FROM comments c
            JOIN post_scores_latest_v s ON c.post_id = s.post_id
            WHERE s.business_pool = 'core' OR s.value_score >= 6;
            """
        )
    elif (
        _relation_exists("comments")
        and _relation_exists("posts_raw")
        and _relation_exists("post_scores_latest_v")
        and _column_exists("comments", "source_post_id")
        and _column_exists("posts_raw", "source_post_id")
        and _column_exists("posts_raw", "id")
    ):
        # Compatible path: comments table doesn't store post_id, so join through posts_raw.
        op.execute(
            """
            CREATE OR REPLACE VIEW v_comment_semantic_tasks AS
            SELECT
                c.id AS comment_id,
                c.reddit_comment_id,
                c.source_post_id,
                c.subreddit,
                LEFT(c.body, 1200) AS text_for_llm,
                c.score,
                c.depth,
                c.created_utc,
                c.fetched_at,
                c.lang,
                c.source_track,
                c.first_seen_at
            FROM comments c
            JOIN posts_raw p
              ON p.source_post_id = c.source_post_id
             AND p.is_current = TRUE
            JOIN post_scores_latest_v s ON s.post_id = p.id
            WHERE s.business_pool = 'core' OR s.value_score >= 6;
            """
        )
    elif _relation_exists("comments"):
        # Safe fallback: keep the view valid but empty.
        op.execute(
            """
            CREATE OR REPLACE VIEW v_comment_semantic_tasks AS
            SELECT
                c.id AS comment_id,
                c.reddit_comment_id,
                c.source_post_id,
                c.subreddit,
                LEFT(c.body, 1200) AS text_for_llm,
                c.score,
                c.depth,
                c.created_utc,
                c.fetched_at,
                c.lang,
                c.source_track,
                c.first_seen_at
            FROM comments c
            WHERE FALSE;
            """
        )

    # 3) Create “正常业务口径” comments view (core+lab)
    if _relation_exists("comments"):
        op.execute(
            """
            CREATE OR REPLACE VIEW comments_core_lab_v AS
            SELECT c.*
            FROM comments c
            LEFT JOIN comment_scores_latest_v s ON s.comment_id = c.id
            WHERE COALESCE(s.business_pool, c.business_pool, 'lab') IN ('core','lab');
            """
        )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS comments_core_lab_v")
    # Restore v_comment_semantic_tasks to a safe fallback (no dependency on *_latest_v).
    if _relation_exists("comments"):
        op.execute(
            """
            CREATE OR REPLACE VIEW v_comment_semantic_tasks AS
            SELECT
                c.id AS comment_id,
                c.reddit_comment_id,
                c.source_post_id,
                c.subreddit,
                LEFT(c.body, 1200) AS text_for_llm,
                c.score,
                c.depth,
                c.created_utc,
                c.fetched_at,
                c.lang,
                c.source_track,
                c.first_seen_at
            FROM comments c
            WHERE FALSE;
            """
        )
    op.execute("DROP VIEW IF EXISTS comment_scores_latest_v")
    op.execute("DROP VIEW IF EXISTS post_scores_latest_v")
