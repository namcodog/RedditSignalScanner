"""Prefer primary score rule_version in latest score views."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251223_000001"
down_revision: str | None = "20251222_000004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_PRIMARY_RULE_VERSION = "rulebook_v1"


def _table_exists(name: str) -> bool:
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
    if _view_has_column("post_scores_latest_v", "id"):
        return True
    return not _table_exists("post_scores_latest_v")


def _get_view_columns(view_name: str) -> list[dict[str, object]]:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT column_name,
                   data_type,
                   character_maximum_length,
                   numeric_precision,
                   numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :view_name
            ORDER BY ordinal_position
            """
        ),
        {"view_name": view_name},
    )
    return [dict(row) for row in result.mappings().all()]


def _column_type_sql(column: dict[str, object]) -> str:
    data_type = column.get("data_type")
    if data_type == "character varying":
        length = column.get("character_maximum_length")
        return f"character varying({length})" if length else "character varying"
    if data_type == "timestamp with time zone":
        return "timestamptz"
    if data_type == "numeric":
        precision = column.get("numeric_precision")
        scale = column.get("numeric_scale")
        if precision is not None and scale is not None:
            return f"numeric({precision},{scale})"
        return "numeric"
    return str(data_type)


def _build_view_select(
    *,
    table_name: str,
    view_name: str,
    fallback_columns: list[str],
    prefer_primary: bool,
) -> str:
    view_columns = _get_view_columns(view_name)
    if not view_columns:
        select_list = ",\n               ".join(fallback_columns)
    else:
        select_list = ",\n               ".join(
            f"{col['column_name']}::{_column_type_sql(col)} AS {col['column_name']}"
            for col in view_columns
        )
    if not prefer_primary:
        return f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT {select_list}
            FROM {table_name}
            WHERE is_latest = true;
            """
    return f"""
        CREATE OR REPLACE VIEW {view_name} AS
        WITH has_primary AS (
            SELECT EXISTS (
                SELECT 1
                FROM {table_name}
                WHERE is_latest = true
                  AND rule_version <> '{_PRIMARY_RULE_VERSION}'
            ) AS has_primary
        )
        SELECT {select_list}
        FROM {table_name}, has_primary
        WHERE is_latest = true
          AND (
            (has_primary.has_primary = false AND rule_version = '{_PRIMARY_RULE_VERSION}')
            OR (has_primary.has_primary = true AND rule_version <> '{_PRIMARY_RULE_VERSION}')
          );
        """


def _create_post_scores_latest_view(*, prefer_primary: bool) -> None:
    if _post_scores_use_id_columns():
        fallback_columns = [
            "id",
            "post_id",
            "llm_version",
            "rule_version",
            "scored_at",
            "is_latest",
            "value_score",
            "opportunity_score",
            "business_pool",
            "sentiment",
            "purchase_intent_score",
            "tags_analysis",
            "entities_extracted",
            "calculation_log",
        ]
    else:
        fallback_columns = [
            "post_id",
            "rule_version",
            "llm_version",
            "value_score",
            "opportunity_score",
            "business_pool",
            "sentiment",
            "purchase_intent_score",
            "tags_analysis",
            "entities_extracted",
            "calculation_log",
            "scored_at",
        ]
    op.execute(
        _build_view_select(
            table_name="post_scores",
            view_name="post_scores_latest_v",
            fallback_columns=fallback_columns,
            prefer_primary=prefer_primary,
        )
    )


def _create_comment_scores_latest_view(*, prefer_primary: bool) -> None:
    fallback_columns = [
        "comment_id",
        "rule_version",
        "llm_version",
        "value_score",
        "opportunity_score",
        "business_pool",
        "sentiment",
        "purchase_intent_score",
        "tags_analysis",
        "entities_extracted",
        "calculation_log",
        "scored_at",
    ]
    op.execute(
        _build_view_select(
            table_name="comment_scores",
            view_name="comment_scores_latest_v",
            fallback_columns=fallback_columns,
            prefer_primary=prefer_primary,
        )
    )


def upgrade() -> None:
    if _table_exists("post_scores"):
        _create_post_scores_latest_view(prefer_primary=True)
    if _table_exists("comment_scores"):
        _create_comment_scores_latest_view(prefer_primary=True)


def downgrade() -> None:
    if _table_exists("post_scores"):
        _create_post_scores_latest_view(prefer_primary=False)
    if _table_exists("comment_scores"):
        _create_comment_scores_latest_view(prefer_primary=False)
