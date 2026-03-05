from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import ContentLabel, ContentEntity, ContentType
from app.services.semantic.text_classifier import classify_category_aspect
from app.services.labeling.labeling_service import _extract_entities_from_text


async def label_posts_recent(session: AsyncSession, *, since_days: int = 7, limit: int = 500) -> dict[str, int]:
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    # 选择 posts_hot 作为近实时来源
    res = await session.execute(
        text(
            """
            SELECT id, COALESCE(title,'') || ' ' || COALESCE(body,'') AS text
            FROM posts_hot
            WHERE created_at >= :since
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"since": since_dt, "lim": max(1, min(2000, limit))},
    )
    rows = list(res.mappings())
    if not rows:
        return {"labeled": 0, "entities": 0}
    labeled = 0
    ents = 0
    for r in rows:
        pid = int(r["id"])
        textv = str(r["text"] or "")
        # label
        cls = classify_category_aspect(textv)
        await session.merge(
            ContentLabel(
                content_type=ContentType.POST.value,
                content_id=pid,
                category=cls.category.value,
                aspect=cls.aspect.value,
                sentiment_score=cls.sentiment_score,
                sentiment_label=cls.sentiment_label,
                confidence=80,
            )
        )
        labeled += 1
        # entities
        for name, etype in _extract_entities_from_text(textv):
            await session.merge(
                ContentEntity(
                    content_type=ContentType.POST.value,
                    content_id=pid,
                    entity=name,
                    entity_type=etype.value,
                    count=1,
                )
            )
            ents += 1
    await session.commit()
    return {"labeled": labeled, "entities": ents}
