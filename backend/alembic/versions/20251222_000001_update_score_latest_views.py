"""Update score latest views to honor is_latest only.

Revision ID: 20251222_000001
Revises: 20251218_000005
Create Date: 2025-12-22
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251222_000001"
down_revision: str | None = "20251218_000005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _relation_exists(name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
        return result.scalar() is not None
    except Exception:
        return False


def _view_has_column(view_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :view_name
                  AND column_name = :column_name
                LIMIT 1
                """
            ),
            {"view_name": view_name, "column_name": column_name},
        )
        return result.first() is not None
    except Exception:
        return False


def _post_scores_use_id_columns() -> bool:
    # Keep existing column order to avoid CREATE OR REPLACE VIEW rename errors.
    if _view_has_column("post_scores_latest_v", "id"):
        return True
    return not _relation_exists("post_scores_latest_v")


def _post_scores_latest_view_sql(*, use_id_columns: bool, with_rulebook_filter: bool) -> str:
    rulebook_filter = " AND rule_version = 'rulebook_v1'" if with_rulebook_filter else ""
    if use_id_columns:
        return f"""
            CREATE OR REPLACE VIEW post_scores_latest_v AS
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
            WHERE is_latest = true{rulebook_filter};
            """
    return f"""
            CREATE OR REPLACE VIEW post_scores_latest_v AS
            SELECT post_id,
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
            FROM post_scores
            WHERE is_latest = true{rulebook_filter};
            """


def _post_scores_latest_view_placeholder_sql(*, use_id_columns: bool) -> str:
    if use_id_columns:
        return """
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
    return """
            CREATE OR REPLACE VIEW post_scores_latest_v AS
            SELECT
                NULL::bigint AS post_id,
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


def upgrade() -> None:
    # post_scores_latest_v: keep latest by is_latest (no rule_version lock)
    use_id_columns = _post_scores_use_id_columns()
    if _relation_exists("post_scores"):
        op.execute(
            _post_scores_latest_view_sql(
                use_id_columns=use_id_columns,
                with_rulebook_filter=False,
            )
        )
    else:
        op.execute(_post_scores_latest_view_placeholder_sql(use_id_columns=use_id_columns))

    # comment_scores_latest_v: keep latest by is_latest (no rule_version lock)
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
            WHERE is_latest = true;
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


def downgrade() -> None:
    use_id_columns = _post_scores_use_id_columns()
    if _relation_exists("post_scores"):
        op.execute(
            _post_scores_latest_view_sql(
                use_id_columns=use_id_columns,
                with_rulebook_filter=True,
            )
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
