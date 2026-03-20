"""Fix posts_raw SCD2 trigger contract.

Revision ID: 20260317_000001
Revises: 20260311_000001
Create Date: 2026-03-17 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260317_000001"
down_revision: Union[str, tuple[str, ...], None] = "20260311_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.trg_posts_raw_enforce_scd2()
        RETURNS trigger AS $$
        BEGIN
          IF NEW.is_current THEN
            UPDATE public.posts_raw
              SET is_current = false,
                  valid_to   = LEAST(COALESCE(NEW.valid_from, now()), now())
            WHERE source = NEW.source
              AND source_post_id = NEW.source_post_id
              AND is_current = true
              AND id <> COALESCE(NEW.id, -1);
          END IF;

          IF NEW.valid_to IS NULL THEN
            NEW.valid_to := '9999-12-31 00:00:00+00'::timestamptz;
          END IF;
          IF NEW.valid_from IS NULL THEN
            NEW.valid_from := now();
          END IF;
          IF NEW.valid_from >= NEW.valid_to THEN
            NEW.valid_to := NEW.valid_from + interval '1 second';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS enforce_scd2_posts_raw ON public.posts_raw")
    op.execute(
        """
        CREATE TRIGGER enforce_scd2_posts_raw
        BEFORE INSERT OR UPDATE ON public.posts_raw
        FOR EACH ROW
        EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2()
        """
    )

    op.execute(
        """
        ALTER TABLE public.posts_raw
          ALTER COLUMN valid_to SET DEFAULT '9999-12-31 00:00:00+00'::timestamptz;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.trg_posts_raw_enforce_scd2()
        RETURNS trigger AS $$
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                NEW.version := COALESCE(NEW.version, 1);
                NEW.is_current := COALESCE(NEW.is_current, true);
                NEW.valid_from := COALESCE(NEW.valid_from, NOW());
                NEW.valid_to := COALESCE(NEW.valid_to, '9999-12-31 00:00:00'::timestamp);
                RETURN NEW;
            END IF;

            IF (TG_OP = 'UPDATE') THEN
                IF (NEW.title IS DISTINCT FROM OLD.title OR NEW.body IS DISTINCT FROM OLD.body) THEN
                    UPDATE public.posts_raw
                    SET is_current = false,
                        valid_to = NOW()
                    WHERE id = OLD.id;

                    INSERT INTO public.posts_raw (
                        source, source_post_id, version,
                        created_at, fetched_at, valid_from, valid_to, is_current,
                        author_id, author_name, title, body, body_norm, text_norm_hash,
                        url, subreddit, score, num_comments, is_deleted, edit_count, lang, metadata
                    ) VALUES (
                        NEW.source, NEW.source_post_id, COALESCE(NEW.version, OLD.version + 1),
                        OLD.created_at, NOW(), NOW(), '9999-12-31 00:00:00', true,
                        NEW.author_id, NEW.author_name, NEW.title, NEW.body, NEW.body_norm, NEW.text_norm_hash,
                        NEW.url, NEW.subreddit, NEW.score, NEW.num_comments, NEW.is_deleted, NEW.edit_count, NEW.lang, NEW.metadata
                    );
                    RETURN NULL;
                ELSE
                    NEW.version := OLD.version;
                    NEW.valid_from := OLD.valid_from;
                    NEW.valid_to := OLD.valid_to;
                    NEW.is_current := OLD.is_current;
                    RETURN NEW;
                END IF;
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS enforce_scd2_posts_raw ON public.posts_raw")
    op.execute(
        """
        CREATE TRIGGER enforce_scd2_posts_raw
        BEFORE INSERT OR UPDATE ON public.posts_raw
        FOR EACH ROW
        EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2()
        """
    )

    op.execute(
        """
        ALTER TABLE public.posts_raw
          ALTER COLUMN valid_to SET DEFAULT '9999-12-31 00:00:00'::timestamp;
        """
    )
