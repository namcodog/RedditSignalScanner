from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.comment import ContentLabel


@pytest.mark.asyncio
async def test_content_label_allows_legacy_freeform_category_and_aspect() -> None:
    """防止 worker 因历史/回填的自由文本标签刷屏报错。

    背景：content_labels.category/aspect 在历史数据里可能出现 pain_tag/aspect_tag 之类值，
    如果 ORM 仍用 Enum 强校验，会在读取时抛 LookupError。
    """
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        community_name = f"r/test_legacy_labels_{uuid.uuid4().hex[:8]}"
        community_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO community_pool (
                        name, tier, categories, description_keywords,
                        semantic_quality_score, is_active, is_blacklisted,
                        created_at, updated_at
                    ) VALUES (
                        :name, 'candidate', '{}'::jsonb, '{}'::jsonb,
                        0.5, true, false, :ts, :ts
                    )
                    RETURNING id
                    """
                ),
                {"name": community_name, "ts": now},
            )
        ).scalar_one()

        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES (
                        'reddit', :pid, 1, :ts,
                        :ts, :ts, :sub, 'title', 'body', true, :community_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "pid": f"t3_legacy_{uuid.uuid4().hex[:10]}",
                    "ts": now,
                    "sub": community_name,
                    "community_id": int(community_id),
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
                VALUES ('post', :cid, 'pain_tag', 'some_new_aspect_tag', 90)
                """
            ),
            {"cid": int(post_id)},
        )
        await session.commit()

        fetched = (
            await session.execute(
                select(ContentLabel).where(
                    ContentLabel.content_type == "post",
                    ContentLabel.content_id == int(post_id),
                )
            )
        ).scalars().all()
        assert any(
            (lbl.category == "pain_tag" and lbl.aspect == "some_new_aspect_tag") for lbl in fetched
        )
