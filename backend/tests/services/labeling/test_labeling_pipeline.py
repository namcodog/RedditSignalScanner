from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.crawl.comments_ingest import persist_comments
from app.services.labeling.labeling_service import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)


@pytest.mark.asyncio
async def test_labeling_and_entities_for_comments() -> None:
    async with SessionFactory() as session:
        # insert one comment
        await persist_comments(
            session,
            source_post_id="t3_postx",
            subreddit="r/homegym",
            comments=[
                {
                    "id": "t1_labc",
                    "body": "Tonal subscription fee is too high.",
                    "created_utc": datetime.now(timezone.utc),
                    "depth": 0,
                    "score": 1,
                }
            ],
        )
        await session.commit()

        # labeling
        n1 = await classify_and_label_comments(session, ["t1_labc"])
        n2 = await extract_and_label_entities_for_comments(session, ["t1_labc"])
        await session.commit()
        assert n1 == 1
        assert n2 >= 1

        # check content_labels
        row = await session.execute(
            text(
                "SELECT category, aspect FROM content_labels cl JOIN comments c ON cl.content_id=c.id WHERE c.reddit_comment_id='t1_labc'"
            )
        )
        cat, asp = row.fetchone()
        assert cat in ("pain", "solution", "other")
        # subscription keyword triggers subscription aspect
        assert asp in ("subscription", "price", "content", "install", "ecosystem", "strength", "other")

        # check content_entities
        row2 = await session.execute(
            text(
                "SELECT entity FROM content_entities ce JOIN comments c ON ce.content_id=c.id WHERE c.reddit_comment_id='t1_labc'"
            )
        )
        entities = [r[0] for r in row2.fetchall()]
        assert any("tonal" in e for e in entities)

