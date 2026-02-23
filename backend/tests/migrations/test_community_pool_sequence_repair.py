from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sequence_repair import repair_serial_pk_sequence


@pytest.mark.asyncio
async def test_repair_serial_pk_sequence_unblocks_inserts(
    db_session: AsyncSession,
) -> None:
    # Seed a row with a known id, then force the sequence to hand out the same id again.
    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                id, name, tier, categories, description_keywords, semantic_quality_score
            )
            VALUES (
                9, 'r/sequence_existing', 'high', '[]'::jsonb, '{}'::jsonb, 0.50
            )
            """
        )
    )
    await db_session.commit()

    await db_session.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('public.community_pool', 'id'),
                8,
                true
            )
            """
        )
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO community_pool (
                    name, tier, categories, description_keywords, semantic_quality_score
                )
                VALUES (
                    'r/sequence_new', 'high', '[]'::jsonb, '{}'::jsonb, 0.50
                )
                """
            )
        )
        await db_session.commit()

    await db_session.rollback()

    await repair_serial_pk_sequence(
        db_session,
        table_regclass="public.community_pool",
        pk_column="id",
    )

    await db_session.execute(
        text(
            """
            INSERT INTO community_pool (
                name, tier, categories, description_keywords, semantic_quality_score
            )
            VALUES (
                'r/sequence_new', 'high', '[]'::jsonb, '{}'::jsonb, 0.50
            )
            """
        )
    )
    await db_session.commit()

    inserted_id = (
        await db_session.execute(
            text("SELECT id FROM community_pool WHERE name = 'r/sequence_new'")
        )
    ).scalar_one()
    assert inserted_id >= 10

