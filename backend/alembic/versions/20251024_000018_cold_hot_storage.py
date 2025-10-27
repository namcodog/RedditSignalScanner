"""Manage cold/hot storage schema via Alembic and upgrade hashing"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from alembic import op


revision = "20251024_000018"
down_revision = "d18c3d80c75e"
branch_labels = None
depends_on = None


POSTS_RAW_INDEXES = [
    ("idx_posts_raw_created_at", "created_at DESC"),
    ("idx_posts_raw_fetched_at", "fetched_at DESC"),
    ("idx_posts_raw_subreddit", "subreddit, created_at DESC"),
    ("idx_posts_raw_text_hash", "text_norm_hash"),
    ("idx_posts_raw_source_post_id", "source, source_post_id"),
]


def _ensure_posts_raw_table(conn) -> None:
    inspector = sa.inspect(conn)
    if not inspector.has_table("posts_raw"):
        op.create_table(
            "posts_raw",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="reddit"),
            sa.Column("source_post_id", sa.String(length=100), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column(
                "fetched_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "valid_from",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "valid_to",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
                server_default=sa.text("'9999-12-31'::TIMESTAMP"),
            ),
            sa.Column(
                "is_current",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("TRUE"),
            ),
            sa.Column("author_id", sa.String(length=100)),
            sa.Column("author_name", sa.String(length=100)),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("body", sa.Text()),
            sa.Column("body_norm", sa.Text()),
            sa.Column("text_norm_hash", sa.String(length=64)),
            sa.Column("url", sa.Text()),
            sa.Column("subreddit", sa.String(length=100), nullable=False),
            sa.Column("score", sa.Integer(), server_default="0"),
            sa.Column("num_comments", sa.Integer(), server_default="0"),
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("FALSE")),
            sa.Column("edit_count", sa.Integer(), server_default="0"),
            sa.Column("lang", sa.String(length=10)),
            sa.Column("metadata", postgresql.JSONB()),
            sa.UniqueConstraint(
                "source",
                "source_post_id",
                "version",
                name="uq_posts_raw_source_version",
            ),
            sa.CheckConstraint("version > 0", name="ck_posts_raw_version_positive"),
            sa.CheckConstraint(
                "valid_from < valid_to OR valid_to = '9999-12-31'::TIMESTAMP",
                name="ck_posts_raw_valid_period",
            ),
        )

        for index_name, expression in POSTS_RAW_INDEXES:
            op.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON posts_raw ({expression})"
            )

        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_posts_raw_current
            ON posts_raw (source, source_post_id, is_current)
            WHERE is_current = TRUE
            """
        )

    else:
        # Ensure primary key is on id
        pk = inspector.get_pk_constraint("posts_raw")
        if pk and pk.get("constrained_columns") and pk["constrained_columns"] != ["id"]:
            op.drop_constraint(pk["name"], "posts_raw", type_="primary")
            op.create_primary_key("pk_posts_raw", "posts_raw", ["id"])

        # Ensure unique constraint exists
        uqs = {uc["name"] for uc in inspector.get_unique_constraints("posts_raw")}
        if "uq_posts_raw_source_version" not in uqs:
            op.create_unique_constraint(
                "uq_posts_raw_source_version",
                "posts_raw",
                ["source", "source_post_id", "version"],
            )

        # Create missing indexes
        for index_name, expression in POSTS_RAW_INDEXES:
            op.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON posts_raw ({expression})"
            )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_posts_raw_current
            ON posts_raw (source, source_post_id, is_current)
            WHERE is_current = TRUE
            """
        )


def _ensure_posts_hot_table(conn) -> None:
    inspector = sa.inspect(conn)
    if not inspector.has_table("posts_hot"):
        # 创建表时不定义主键,让 conftest.py 或后续迁移处理
        op.create_table(
            "posts_hot",
            sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="reddit"),
            sa.Column("source_post_id", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column(
                "cached_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "expires_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now() + INTERVAL '24 hours'"),
            ),
            sa.Column("author_id", sa.String(length=100)),
            sa.Column("author_name", sa.String(length=100)),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("body", sa.Text()),
            sa.Column("subreddit", sa.String(length=100), nullable=False),
            sa.Column("score", sa.Integer(), server_default="0"),
            sa.Column("num_comments", sa.Integer(), server_default="0"),
            sa.Column("metadata", postgresql.JSONB()),
            sa.UniqueConstraint(
                "source",
                "source_post_id",
                name="uq_posts_hot_source_post",
            ),
        )

        # 创建序列
        op.execute("CREATE SEQUENCE IF NOT EXISTS posts_hot_id_seq")
        op.execute("ALTER TABLE posts_hot ALTER COLUMN id SET DEFAULT nextval('posts_hot_id_seq')")

        # 检查主键是否已存在,如果不存在则创建
        pk_exists = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'posts_hot_pkey'
                    AND conrelid = 'posts_hot'::regclass
                )
                """
            )
        ).scalar()

        if not pk_exists:
            op.execute("ALTER TABLE posts_hot ADD CONSTRAINT posts_hot_pkey PRIMARY KEY (id)")

        # 创建索引
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_hot_expires_at ON posts_hot (expires_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_hot_subreddit ON posts_hot (subreddit, created_at DESC)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_hot_created_at ON posts_hot (created_at DESC)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_hot_metadata_gin ON posts_hot USING gin (metadata)"
        )
    else:
        # 表已存在,确保主键存在
        pk_exists = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'posts_hot_pkey'
                    AND conrelid = 'posts_hot'::regclass
                )
                """
            )
        ).scalar()

        if not pk_exists:
            # 确保 id 列存在
            columns = {col["name"] for col in inspector.get_columns("posts_hot")}
            if "id" not in columns:
                op.execute("CREATE SEQUENCE IF NOT EXISTS posts_hot_id_seq")
                op.execute("ALTER TABLE posts_hot ADD COLUMN id BIGINT DEFAULT nextval('posts_hot_id_seq') NOT NULL")

            # 添加主键
            op.execute("ALTER TABLE posts_hot ADD CONSTRAINT posts_hot_pkey PRIMARY KEY (id)")

        # 确保 author 字段存在
        columns = {col["name"] for col in inspector.get_columns("posts_hot")}
        if "author_id" not in columns:
            op.add_column(
                "posts_hot",
                sa.Column("author_id", sa.String(length=100), nullable=True),
            )
        if "author_name" not in columns:
            op.add_column(
                "posts_hot",
                sa.Column("author_name", sa.String(length=100), nullable=True),
            )


def _ensure_posts_latest_view(conn) -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS posts_latest AS
        SELECT *
        FROM posts_raw
        WHERE is_current = TRUE
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_latest_unique
        ON posts_latest (source, source_post_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posts_latest_created_at
        ON posts_latest (created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posts_latest_subreddit
        ON posts_latest (subreddit, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posts_latest_text_hash
        ON posts_latest (text_norm_hash)
        """
    )


def _cleanup_pending_community_constraints() -> None:
    op.execute(
        """
        ALTER TABLE pending_communities
        DROP CONSTRAINT IF EXISTS fk_pending_communities_discovered_from_task_id_tasks
        """
    )


def _ensure_functions_and_triggers(conn) -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("DROP FUNCTION IF EXISTS text_norm_hash(TEXT)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION text_norm_hash(content TEXT)
        RETURNS TEXT AS $$
        DECLARE
            normalized TEXT;
        BEGIN
            normalized := regexp_replace(
                lower(trim(COALESCE(content, ''))),
                '[^a-z0-9\\s]',
                '',
                'g'
            );
            normalized := regexp_replace(normalized, '\\s+', ' ', 'g');

            RETURN encode(digest(normalized, 'sha256'), 'hex');
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fill_normalized_fields()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.body_norm := regexp_replace(
                regexp_replace(lower(trim(COALESCE(NEW.body, ''))), '[^a-z0-9\\s]', '', 'g'),
                '\\s+',
                ' ',
                'g'
            );

            NEW.text_norm_hash := text_norm_hash(NEW.title || ' ' || COALESCE(NEW.body, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Ensure trigger exists
    trigger_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM pg_trigger
            WHERE tgname = 'trg_fill_normalized_fields'
            """
        )
    ).scalar()
    if not trigger_exists:
        op.execute(
            """
            CREATE TRIGGER trg_fill_normalized_fields
            BEFORE INSERT OR UPDATE ON posts_raw
            FOR EACH ROW
            EXECUTE FUNCTION fill_normalized_fields()
            """
        )

    # Refresh function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_posts_latest()
        RETURNS INTEGER AS $$
        DECLARE
            refresh_count INTEGER;
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY posts_latest;
            GET DIAGNOSTICS refresh_count = ROW_COUNT;
            RETURN refresh_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Cleanup functions
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_hot_cache()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM posts_hot WHERE expires_at < NOW();
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_old_posts(days_to_keep INTEGER DEFAULT 90)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
            cutoff_date TIMESTAMP WITH TIME ZONE;
        BEGIN
            cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

            DELETE FROM posts_raw
            WHERE created_at < cutoff_date
              AND is_current = FALSE;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_storage_stats()
        RETURNS TABLE (
            metric VARCHAR(50),
            value BIGINT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 'posts_raw_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw
            UNION ALL
            SELECT 'posts_raw_current'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw WHERE is_current = TRUE
            UNION ALL
            SELECT 'posts_hot_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot
            UNION ALL
            SELECT 'posts_hot_expired'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot WHERE expires_at < NOW()
            UNION ALL
            SELECT 'unique_subreddits'::VARCHAR(50), COUNT(DISTINCT subreddit)::BIGINT FROM posts_raw
            UNION ALL
            SELECT 'total_versions'::VARCHAR(50), SUM(version)::BIGINT FROM posts_raw WHERE is_current = TRUE;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def _upgrade_text_norm_hash(conn) -> None:
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("posts_raw")
    column = next((col for col in columns if col["name"] == "text_norm_hash"), None)
    if column is None:
        return

    # Column already migrated -> nothing to do
    column_type = column.get("type")
    if isinstance(column_type, sa.String) and getattr(column_type, "length", None) == 64:
        return

    # Drop dependent materialized view before altering the column type
    op.execute("DROP MATERIALIZED VIEW IF EXISTS posts_latest")

    op.execute(
        """
        ALTER TABLE posts_raw
        ALTER COLUMN text_norm_hash TYPE VARCHAR(64)
        USING text_norm_hash::TEXT
        """
    )

    op.execute(
        """
        UPDATE posts_raw
        SET text_norm_hash = text_norm_hash(title || ' ' || COALESCE(body, ''))
        """
    )

    # Ensure index still matches text column
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_raw_text_hash ON posts_raw (text_norm_hash)"
    )


def upgrade() -> None:
    conn = op.get_bind()
    _ensure_posts_raw_table(conn)
    _ensure_posts_hot_table(conn)
    _upgrade_text_norm_hash(conn)
    _ensure_posts_latest_view(conn)
    _ensure_functions_and_triggers(conn)
    _cleanup_pending_community_constraints()


def downgrade() -> None:
    """
    此迁移不可逆，因为涉及复杂的数据迁移和结构变更。

    不可逆的原因:
    1. posts_raw 和 posts_hot 表包含已迁移的历史数据
    2. text_norm_hash 字段已从 MD5 升级到 SHA256（需要重新计算所有哈希值）
    3. 触发器、函数和视图依赖新的表结构
    4. 数据已在冷热存储之间重新分配

    如需回滚到此迁移之前的状态，请:
    1. 恢复数据库备份（推荐）
    2. 或联系数据库管理员执行手动数据迁移

    参考文档: docs/database/cold_hot_storage_migration.md
    """
    raise NotImplementedError(
        "❌ Downgrade not supported for cold/hot storage migration.\n\n"
        "This migration involves irreversible data transformations:\n"
        "  - MD5 → SHA256 hash migration for text_norm_hash field\n"
        "  - Data redistribution between cold and hot storage\n"
        "  - Complex trigger and view dependencies\n\n"
        "To rollback:\n"
        "  1. Restore from database backup (recommended)\n"
        "  2. Contact database administrator for manual migration\n\n"
        "See: docs/database/cold_hot_storage_migration.md"
    )
