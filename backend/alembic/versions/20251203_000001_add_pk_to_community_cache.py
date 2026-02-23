"""Add primary key to community_cache.community_name"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251203_000001"
down_revision = "20251129_000041"
branch_labels = None
depends_on = None


from sqlalchemy.engine.reflection import Inspector

def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    pk = inspector.get_pk_constraint("community_cache")
    
    # Only create PK if it doesn't exist
    if not pk or not pk.get("constrained_columns"):
        # 防御性去重，防止因历史脏数据导致主键创建失败
        op.execute(
            """
            DELETE FROM community_cache a
            USING community_cache b
            WHERE a.community_name = b.community_name
              AND a.ctid < b.ctid
            """
        )
        op.create_primary_key(
            "pk_community_cache_name", "community_cache", ["community_name"]
        )


def downgrade() -> None:
    op.drop_constraint("pk_community_cache_name", "community_cache", type_="primary")
