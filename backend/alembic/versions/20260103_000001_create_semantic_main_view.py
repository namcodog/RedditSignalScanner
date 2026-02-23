"""Create semantic_main_view (fused semantic SSOT view).

Revision ID: 20260103_000001
Revises: 20251229_000001
Create Date: 2026-01-03
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260103_000001"
down_revision: str | None = "20251229_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _relation_exists(name: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name})
        return result.scalar() is not None
    except Exception:
        return False


def upgrade() -> None:
    # Defensive: keep migrations runnable on legacy DBs (empty view placeholder).
    if not (_relation_exists("posts_raw") and _relation_exists("comments")):
        op.execute(
            """
            CREATE OR REPLACE VIEW semantic_main_view AS
            SELECT
                NULL::text AS content_type,
                NULL::bigint AS content_id,
                '{}'::jsonb AS tags_analysis,
                '[]'::jsonb AS entities_extracted,
                NULL::text AS taxonomy_l1,
                NULL::text AS taxonomy_l2,
                NULL::text AS taxonomy_l3,
                '[]'::jsonb AS content_labels,
                '[]'::jsonb AS content_entities,
                '{}'::jsonb AS provenance
            WHERE FALSE;
            """
        )
        return

    op.execute(
        """
        CREATE OR REPLACE VIEW semantic_main_view AS
        WITH post_rows AS (
            SELECT
                'post'::text AS content_type,
                p.id::bigint AS content_id,
                COALESCE(ps.tags_analysis, '{}'::jsonb) AS tags_analysis,
                COALESCE(ps.entities_extracted, '[]'::jsonb) AS entities_extracted,
                psl.l1_category AS taxonomy_l1,
                psl.l2_business AS taxonomy_l2,
                psl.l3_scene AS taxonomy_l3,
                COALESCE(lbl.labels, '[]'::jsonb) AS content_labels,
                COALESCE(ent.entities, '[]'::jsonb) AS content_entities,
                jsonb_build_object(
                    'has_score', (ps.post_id IS NOT NULL),
                    'score_source', CASE WHEN ps.post_id IS NOT NULL THEN 'post_scores_latest_v' ELSE NULL END,
                    'has_taxonomy', (psl.post_id IS NOT NULL),
                    'taxonomy_source', CASE WHEN psl.post_id IS NOT NULL THEN 'post_semantic_labels' ELSE NULL END,
                    'has_content_labels', (COALESCE(lbl.labels_count, 0) > 0),
                    'labels_source', CASE WHEN (COALESCE(lbl.labels_count, 0) > 0) THEN 'content_labels' ELSE NULL END,
                    'has_content_entities', (COALESCE(ent.entities_count, 0) > 0),
                    'entities_source', CASE WHEN (COALESCE(ent.entities_count, 0) > 0) THEN 'content_entities' ELSE NULL END
                ) AS provenance
            FROM posts_raw p
            LEFT JOIN post_scores_latest_v ps ON ps.post_id = p.id
            LEFT JOIN post_semantic_labels psl ON psl.post_id = p.id
            LEFT JOIN LATERAL (
                SELECT
                    jsonb_agg(
                        jsonb_build_object(
                            'category', cl.category::text,
                            'aspect', cl.aspect::text,
                            'sentiment_label', cl.sentiment_label,
                            'sentiment_score', cl.sentiment_score,
                            'confidence', cl.confidence,
                            'created_at', cl.created_at
                        )
                        ORDER BY cl.created_at
                    ) AS labels,
                    COUNT(*)::int AS labels_count
                FROM content_labels cl
                WHERE cl.content_type::text = 'post'
                  AND cl.content_id = p.id
            ) lbl ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    jsonb_agg(
                        jsonb_build_object(
                            'entity', ce.entity,
                            'entity_type', ce.entity_type::text,
                            'count', ce.count,
                            'created_at', ce.created_at
                        )
                        ORDER BY ce.created_at
                    ) AS entities,
                    COUNT(*)::int AS entities_count
                FROM content_entities ce
                WHERE ce.content_type::text = 'post'
                  AND ce.content_id = p.id
            ) ent ON TRUE
            WHERE p.is_current = TRUE
        ),
        comment_rows AS (
            SELECT
                'comment'::text AS content_type,
                c.id::bigint AS content_id,
                COALESCE(cs.tags_analysis, '{}'::jsonb) AS tags_analysis,
                COALESCE(cs.entities_extracted, '[]'::jsonb) AS entities_extracted,
                NULL::text AS taxonomy_l1,
                NULL::text AS taxonomy_l2,
                NULL::text AS taxonomy_l3,
                COALESCE(lbl.labels, '[]'::jsonb) AS content_labels,
                COALESCE(ent.entities, '[]'::jsonb) AS content_entities,
                jsonb_build_object(
                    'has_score', (cs.comment_id IS NOT NULL),
                    'score_source', CASE WHEN cs.comment_id IS NOT NULL THEN 'comment_scores_latest_v' ELSE NULL END,
                    'has_taxonomy', FALSE,
                    'taxonomy_source', NULL,
                    'has_content_labels', (COALESCE(lbl.labels_count, 0) > 0),
                    'labels_source', CASE WHEN (COALESCE(lbl.labels_count, 0) > 0) THEN 'content_labels' ELSE NULL END,
                    'has_content_entities', (COALESCE(ent.entities_count, 0) > 0),
                    'entities_source', CASE WHEN (COALESCE(ent.entities_count, 0) > 0) THEN 'content_entities' ELSE NULL END
                ) AS provenance
            FROM comments c
            LEFT JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
            LEFT JOIN LATERAL (
                SELECT
                    jsonb_agg(
                        jsonb_build_object(
                            'category', cl.category::text,
                            'aspect', cl.aspect::text,
                            'sentiment_label', cl.sentiment_label,
                            'sentiment_score', cl.sentiment_score,
                            'confidence', cl.confidence,
                            'created_at', cl.created_at
                        )
                        ORDER BY cl.created_at
                    ) AS labels,
                    COUNT(*)::int AS labels_count
                FROM content_labels cl
                WHERE cl.content_type::text = 'comment'
                  AND cl.content_id = c.id
            ) lbl ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    jsonb_agg(
                        jsonb_build_object(
                            'entity', ce.entity,
                            'entity_type', ce.entity_type::text,
                            'count', ce.count,
                            'created_at', ce.created_at
                        )
                        ORDER BY ce.created_at
                    ) AS entities,
                    COUNT(*)::int AS entities_count
                FROM content_entities ce
                WHERE ce.content_type::text = 'comment'
                  AND ce.content_id = c.id
            ) ent ON TRUE
        )
        SELECT * FROM post_rows
        UNION ALL
        SELECT * FROM comment_rows;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS semantic_main_view")

