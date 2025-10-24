"""add audit fields and indexes"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "aef64335bd34"
down_revision = "20251022_000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- community_pool ---
    op.alter_column(
        "community_pool",
        "categories",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="categories::jsonb",
    )
    op.alter_column(
        "community_pool",
        "description_keywords",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="description_keywords::jsonb",
    )

    op.add_column(
        "community_pool",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "community_pool",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "community_pool",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_pool",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_community_pool_created_by_users",
        "community_pool",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_pool_updated_by_users",
        "community_pool",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_pool_deleted_by_users",
        "community_pool",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create GIN indexes with IF NOT EXISTS
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_pool_categories_gin
        ON community_pool USING gin (categories)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_pool_keywords_gin
        ON community_pool USING gin (description_keywords)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_pool_deleted_at
        ON community_pool (deleted_at)
    """)

    # --- pending_communities ---
    op.add_column(
        "pending_communities",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "pending_communities",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "pending_communities",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pending_communities",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pending_communities",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pending_communities",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_pending_communities_discovered_task",
        "pending_communities",
        "tasks",
        ["discovered_from_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pending_communities_reviewed_user",
        "pending_communities",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pending_communities_created_user",
        "pending_communities",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pending_communities_updated_user",
        "pending_communities",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pending_communities_deleted_user",
        "pending_communities",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create indexes with IF NOT EXISTS to avoid conflicts with existing indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_task_id
        ON pending_communities (discovered_from_task_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_reviewed_by
        ON pending_communities (reviewed_by)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_status
        ON pending_communities (status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_deleted_at
        ON pending_communities (deleted_at)
    """)

    # --- community_import_history ---
    op.alter_column(
        "community_import_history",
        "uploaded_by_user_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.add_column(
        "community_import_history",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "community_import_history",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_community_import_history_created_by_users",
        "community_import_history",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_import_history_updated_by_users",
        "community_import_history",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Create indexes with IF NOT EXISTS
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_import_history_uploaded_by
        ON community_import_history (uploaded_by_user_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_import_history_created_at
        ON community_import_history (created_at)
    """)

    # --- posts_raw primary key adjustment ---
    # Check if posts_raw table exists before modifying it
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'posts_raw'
        )
    """))
    posts_raw_exists = result.scalar()

    if posts_raw_exists:
        op.execute("UPDATE posts_raw SET id = nextval('posts_raw_id_seq') WHERE id IS NULL")
        op.alter_column("posts_raw", "id", nullable=False)
        op.drop_constraint("pk_posts_raw", "posts_raw", type_="primary")
        op.create_primary_key("pk_posts_raw", "posts_raw", ["id"])
        op.create_unique_constraint(
            "uq_posts_raw_source_version",
            "posts_raw",
            ["source", "source_post_id", "version"],
        )

    # --- posts_hot primary key adjustment ---
    # Check if posts_hot table exists before modifying it
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'posts_hot'
        )
    """))
    posts_hot_exists = result.scalar()

    if posts_hot_exists:
        op.execute(
            "CREATE SEQUENCE IF NOT EXISTS posts_hot_id_seq OWNED BY posts_hot.id"
        )
        op.add_column(
            "posts_hot",
            sa.Column(
                "id",
                sa.BigInteger(),
                server_default=sa.text("nextval('posts_hot_id_seq')"),
                nullable=False,
            ),
        )
        op.drop_constraint("pk_posts_hot", "posts_hot", type_="primary")
        op.create_primary_key("pk_posts_hot", "posts_hot", ["id"])
        op.create_unique_constraint(
            "uq_posts_hot_source_post",
            "posts_hot",
            ["source", "source_post_id"],
        )
        # Create GIN index with IF NOT EXISTS
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_hot_metadata_gin
            ON posts_hot USING gin (metadata)
        """)

    # clean default now that existing rows populated
    op.alter_column(
        "posts_hot",
        "id",
        server_default=None,
    )

    op.alter_column(
        "pending_communities",
        "created_at",
        server_default=None,
    )
    op.alter_column(
        "pending_communities",
        "updated_at",
        server_default=None,
    )


def downgrade() -> None:
    # --- posts_hot ---
    op.drop_index("idx_posts_hot_metadata_gin", table_name="posts_hot")
    op.drop_constraint("uq_posts_hot_source_post", "posts_hot", type_="unique")
    op.drop_constraint("pk_posts_hot", "posts_hot", type_="primary")
    op.create_primary_key(
        "pk_posts_hot", "posts_hot", ["source", "source_post_id"]
    )
    op.drop_column("posts_hot", "id")
    op.execute("DROP SEQUENCE IF EXISTS posts_hot_id_seq")

    # --- posts_raw ---
    op.drop_constraint("uq_posts_raw_source_version", "posts_raw", type_="unique")
    op.drop_constraint("pk_posts_raw", "posts_raw", type_="primary")
    op.create_primary_key(
        "pk_posts_raw", "posts_raw", ["source", "source_post_id", "version"]
    )
    op.alter_column("posts_raw", "id", nullable=True)

    # --- community_import_history ---
    op.drop_constraint(
        "fk_community_import_history_updated_by_users",
        "community_import_history",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_import_history_created_by_users",
        "community_import_history",
        type_="foreignkey",
    )
    op.drop_column("community_import_history", "updated_by")
    op.drop_column("community_import_history", "created_by")
    op.alter_column(
        "community_import_history",
        "uploaded_by_user_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.drop_index(
        "idx_community_import_history_created_at",
        table_name="community_import_history",
    )
    op.drop_index(
        "idx_community_import_history_uploaded_by",
        table_name="community_import_history",
    )

    # --- pending_communities ---
    op.drop_index(
        "idx_pending_communities_deleted_at",
        table_name="pending_communities",
    )
    op.drop_index(
        "idx_pending_communities_status", table_name="pending_communities"
    )
    op.drop_index(
        "idx_pending_communities_reviewed_by",
        table_name="pending_communities",
    )
    op.drop_index(
        "idx_pending_communities_task_id", table_name="pending_communities"
    )

    op.drop_constraint(
        "fk_pending_communities_deleted_user",
        "pending_communities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_communities_updated_user",
        "pending_communities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_communities_created_user",
        "pending_communities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_communities_reviewed_user",
        "pending_communities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_communities_discovered_task",
        "pending_communities",
        type_="foreignkey",
    )

    op.drop_column("pending_communities", "deleted_by")
    op.drop_column("pending_communities", "deleted_at")
    op.drop_column("pending_communities", "updated_by")
    op.drop_column("pending_communities", "created_by")
    op.drop_column("pending_communities", "updated_at")
    op.drop_column("pending_communities", "created_at")

    # --- community_pool ---
    op.drop_index("idx_community_pool_deleted_at", table_name="community_pool")
    op.drop_index("idx_community_pool_keywords_gin", table_name="community_pool")
    op.drop_index("idx_community_pool_categories_gin", table_name="community_pool")

    op.drop_constraint(
        "fk_community_pool_deleted_by_users",
        "community_pool",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_pool_updated_by_users",
        "community_pool",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_pool_created_by_users",
        "community_pool",
        type_="foreignkey",
    )
    op.drop_column("community_pool", "deleted_by")
    op.drop_column("community_pool", "deleted_at")
    op.drop_column("community_pool", "updated_by")
    op.drop_column("community_pool", "created_by")

    op.alter_column(
        "community_pool",
        "description_keywords",
        existing_type=postgresql.JSONB(),
        type_=sa.JSON(),
        postgresql_using="description_keywords::json",
    )
    op.alter_column(
        "community_pool",
        "categories",
        existing_type=postgresql.JSONB(),
        type_=sa.JSON(),
        postgresql_using="categories::json",
    )
