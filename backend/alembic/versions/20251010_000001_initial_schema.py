"""Initial schema for Reddit Signal Scanner core tables."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20251010_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    task_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="task_status",
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="ck_users_valid_email",
        ),
    )

    op.create_index("idx_users_email", "users", ["email"])
    op.create_index(
        "idx_users_active",
        "users",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "processing",
                "completed",
                "failed",
                name="task_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'::task_status"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("failure_category", sa.String(length=50), nullable=True),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_letter_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(product_description) BETWEEN 10 AND 2000",
            name="ck_tasks_valid_description_length",
        ),
        sa.CheckConstraint(
            "(completed_at IS NULL) OR (completed_at >= created_at)",
            name="ck_tasks_valid_completion_time",
        ),
        sa.CheckConstraint(
            "(status = 'failed'::task_status AND error_message IS NOT NULL) OR "
            "(status != 'failed'::task_status AND (error_message IS NULL OR error_message = ''))",
            name="ck_tasks_error_message_when_failed",
        ),
        sa.CheckConstraint(
            "(status = 'completed'::task_status AND completed_at IS NOT NULL) OR "
            "(status != 'completed'::task_status AND completed_at IS NULL)",
            name="ck_tasks_completed_status_alignment",
        ),
    )
    op.create_index("idx_tasks_user_status", "tasks", ["user_id", "status"])
    op.create_index("idx_tasks_user_created", "tasks", ["user_id", "created_at"])
    op.create_index("idx_tasks_status", "tasks", ["status"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_insights_schema(data jsonb)
        RETURNS boolean AS $$
        DECLARE
            item jsonb;
        BEGIN
            IF jsonb_typeof(data) != 'object' THEN
                RETURN false;
            END IF;

            IF NOT (data ? 'pain_points' AND data ? 'competitors' AND data ? 'opportunities') THEN
                RETURN false;
            END IF;

            IF jsonb_typeof(data->'pain_points') != 'array'
                OR jsonb_typeof(data->'competitors') != 'array'
                OR jsonb_typeof(data->'opportunities') != 'array' THEN
                RETURN false;
            END IF;

            FOR item IN SELECT * FROM jsonb_array_elements(data->'pain_points') LOOP
                IF NOT (item ? 'description' AND item ? 'frequency' AND item ? 'sentiment_score') THEN
                    RETURN false;
                END IF;
            END LOOP;

            RETURN true;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_sources_schema(data jsonb)
        RETURNS boolean AS $$
        BEGIN
            IF jsonb_typeof(data) != 'object' THEN
                RETURN false;
            END IF;

            IF NOT (data ? 'communities' AND data ? 'posts_analyzed' AND data ? 'cache_hit_rate') THEN
                RETURN false;
            END IF;

            IF jsonb_typeof(data->'communities') != 'array' THEN
                RETURN false;
            END IF;

            IF jsonb_typeof(data->'posts_analyzed') != 'number' THEN
                RETURN false;
            END IF;

            RETURN true;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("insights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("analysis_version", sa.String(length=10), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("validate_insights_schema(insights)", name="ck_analyses_insights_schema"),
        sa.CheckConstraint("validate_sources_schema(sources)", name="ck_analyses_sources_schema"),
        sa.CheckConstraint(
            "(confidence_score IS NULL) OR (confidence_score BETWEEN 0.00 AND 1.00)",
            name="ck_analyses_confidence_score_range",
        ),
    )

    op.create_index("idx_analyses_confidence", "analyses", ["confidence_score"])
    op.create_index("idx_analyses_version", "analyses", ["analysis_version"])
    op.create_index("idx_analyses_created", "analyses", ["created_at"])
    op.create_index(
        "idx_analyses_insights_gin",
        "analyses",
        ["insights"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_analyses_sources_gin",
        "analyses",
        ["sources"],
        postgresql_using="gin",
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("template_version", sa.String(length=10), nullable=False, server_default="1.0"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index("idx_reports_generated", "reports", ["generated_at"])
    op.create_index("idx_reports_template", "reports", ["template_version"])

    op.create_table(
        "community_cache",
        sa.Column("community_name", sa.String(length=100), primary_key=True),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posts_cached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("quality_score", sa.Numeric(3, 2), nullable=False, server_default="0.50"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "crawl_priority",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("posts_cached >= 0", name="ck_community_cache_posts_cached_non_negative"),
        sa.CheckConstraint("ttl_seconds > 0", name="ck_community_cache_positive_ttl"),
        sa.CheckConstraint(
            "crawl_priority BETWEEN 1 AND 100",
            name="ck_community_cache_priority_range",
        ),
    )

    op.create_index("idx_cache_priority", "community_cache", ["crawl_priority"])
    op.create_index("idx_cache_last_crawled", "community_cache", ["last_crawled_at"])
    op.create_index("idx_cache_hit_count", "community_cache", ["hit_count"])
    op.create_index("idx_cache_quality", "community_cache", ["quality_score"])


def downgrade() -> None:
    op.drop_index("idx_cache_quality", table_name="community_cache")
    op.drop_index("idx_cache_hit_count", table_name="community_cache")
    op.drop_index("idx_cache_last_crawled", table_name="community_cache")
    op.drop_index("idx_cache_priority", table_name="community_cache")
    op.drop_table("community_cache")

    op.drop_index("idx_reports_template", table_name="reports")
    op.drop_index("idx_reports_generated", table_name="reports")
    op.drop_table("reports")

    op.drop_index("idx_analyses_sources_gin", table_name="analyses")
    op.drop_index("idx_analyses_insights_gin", table_name="analyses")
    op.drop_index("idx_analyses_created", table_name="analyses")
    op.drop_index("idx_analyses_version", table_name="analyses")
    op.drop_index("idx_analyses_confidence", table_name="analyses")
    op.drop_table("analyses")

    op.execute("DROP FUNCTION IF EXISTS validate_sources_schema(jsonb)")
    op.execute("DROP FUNCTION IF EXISTS validate_insights_schema(jsonb)")

    op.drop_index("idx_tasks_status", table_name="tasks")
    op.drop_index("idx_tasks_user_created", table_name="tasks")
    op.drop_index("idx_tasks_user_status", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("idx_users_active", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS task_status")
