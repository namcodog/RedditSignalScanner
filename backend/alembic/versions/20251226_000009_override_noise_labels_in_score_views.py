"""Override latest score views with noise_labels.

Revision ID: 20251226_000009
Revises: 20251226_000008
Create Date: 2025-12-26

Why:
- Ensure noise_labels always downgrade latest views to noise.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251226_000009"
down_revision: str | None = "20251226_000008"
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


def _select_expr(
    *,
    column_name: str,
    column_type: str | None,
    alias: str,
    apply_noise: bool,
) -> str:
    base = f"{alias}.{column_name}"
    expr = base
    if apply_noise and column_name == "business_pool":
        expr = f"CASE WHEN nl.content_id IS NOT NULL THEN 'noise' ELSE {base} END"
    elif apply_noise and column_name == "value_score":
        expr = f"CASE WHEN nl.content_id IS NOT NULL THEN 0 ELSE {base} END"
    if column_type:
        expr = f"{expr}::{column_type}"
    return f"{expr} AS {column_name}"


def _build_view_select(
    *,
    table_name: str,
    view_name: str,
    fallback_columns: list[str],
    prefer_primary: bool,
    noise_content_type: str,
    noise_join_column: str,
    apply_noise: bool,
) -> str:
    view_columns = _get_view_columns(view_name)
    alias = "s"
    if not view_columns:
        select_list = ",\n               ".join(
            _select_expr(
                column_name=name,
                column_type=None,
                alias=alias,
                apply_noise=apply_noise,
            )
            for name in fallback_columns
        )
    else:
        select_list = ",\n               ".join(
            _select_expr(
                column_name=str(col["column_name"]),
                column_type=_column_type_sql(col),
                alias=alias,
                apply_noise=apply_noise,
            )
            for col in view_columns
        )

    join_noise = ""
    if apply_noise:
        join_noise = (
            f"LEFT JOIN noise_labels nl ON nl.content_type = '{noise_content_type}' "
            f"AND nl.content_id = {alias}.{noise_join_column}"
        )

    if not prefer_primary:
        return f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT {select_list}
            FROM {table_name} {alias}
            {join_noise}
            WHERE {alias}.is_latest = true;
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
        FROM {table_name} {alias}
        CROSS JOIN has_primary
        {join_noise}
        WHERE {alias}.is_latest = true
          AND (
            (has_primary.has_primary = false AND {alias}.rule_version = '{_PRIMARY_RULE_VERSION}')
            OR (has_primary.has_primary = true AND {alias}.rule_version <> '{_PRIMARY_RULE_VERSION}')
          );
        """


def _create_post_scores_latest_view(*, prefer_primary: bool, apply_noise: bool) -> None:
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
            noise_content_type="post",
            noise_join_column="post_id",
            apply_noise=apply_noise,
        )
    )


def _create_comment_scores_latest_view(*, prefer_primary: bool, apply_noise: bool) -> None:
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
            noise_content_type="comment",
            noise_join_column="comment_id",
            apply_noise=apply_noise,
        )
    )


def upgrade() -> None:
    if _table_exists("post_scores"):
        _create_post_scores_latest_view(prefer_primary=True, apply_noise=True)
    if _table_exists("comment_scores"):
        _create_comment_scores_latest_view(prefer_primary=True, apply_noise=True)


def downgrade() -> None:
    if _table_exists("post_scores"):
        _create_post_scores_latest_view(prefer_primary=True, apply_noise=False)
    if _table_exists("comment_scores"):
        _create_comment_scores_latest_view(prefer_primary=True, apply_noise=False)
