"""add GIN index for posts_raw full text"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251205_000005"
down_revision = "10e971cacbb4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_fulltext
            ON posts_raw
            USING GIN (
                to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))
            );
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_posts_fulltext")
