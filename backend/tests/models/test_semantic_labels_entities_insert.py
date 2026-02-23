from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_insert_label_and_entity() -> None:
    async with SessionFactory() as session:
        # Insert a label (string enums accepted, native_enum=False)
        await session.execute(
            text(
                """
                INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
                VALUES ('comment', 12345, 'pain', 'subscription', 90)
                """
            )
        )

        # Insert an entity
        await session.execute(
            text(
                """
                INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                VALUES ('comment', 12345, 'Tonal', 'brand', 2)
                """
            )
        )

        count_labels = await session.execute(
            text("SELECT count(*) FROM content_labels WHERE content_id=12345")
        )
        assert count_labels.scalar() == 1

        count_entities = await session.execute(
            text("SELECT count(*) FROM content_entities WHERE content_id=12345")
        )
        assert count_entities.scalar() == 1

