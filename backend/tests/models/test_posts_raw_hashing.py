"""
验证 posts_raw 的文本哈希使用安全算法并保持可追溯性
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostRaw


def _normalize_text(title: str, body: str | None) -> str:
    """匹配触发器的文本归一化逻辑"""
    combined = f"{title} {body or ''}"
    combined = combined.strip().lower()
    combined = re.sub(r"[^a-z0-9\s]", "", combined)
    combined = re.sub(r"\s+", " ", combined)
    return combined


class TestPostsRawHashing:
    """测试 posts_raw 的 text_norm_hash 计算逻辑"""

    @pytest_asyncio.fixture
    async def db_session(self):
        async with SessionFactory() as session:
            yield session

    @pytest.mark.asyncio
    async def test_text_norm_hash_uses_sha256(self, db_session) -> None:
        title = "Hello Reddit!"
        body = "Signal: 🚀 To the moon???"
        created_at = datetime.now(timezone.utc)

        source_post_id = f"unit-test-hash-{uuid.uuid4().hex[:8]}"
        subreddit = f"r/unittest_{uuid.uuid4().hex[:8]}"
        community = CommunityPool(
            name=subreddit,
            tier="core",
            categories={"source": "test"},
            description_keywords={"keywords": ["test"]},
            daily_posts=1,
            avg_comment_length=120,
            quality_score=0.75,
            priority="medium",
            is_active=True,
        )
        db_session.add(community)
        await db_session.flush()

        stmt = pg_insert(PostRaw).values(
            source="reddit",
            source_post_id=source_post_id,
            version=1,
            created_at=created_at,
            fetched_at=created_at,
            valid_from=created_at,
            subreddit=subreddit,
            community_id=community.id,
            title=title,
            body=body,
        )

        await db_session.execute(stmt)
        await db_session.commit()

        result = await db_session.execute(
            select(PostRaw).where(PostRaw.source_post_id == source_post_id)
        )
        record = result.scalar_one()

        expected = hashlib.sha256(
            _normalize_text(title, body).encode("utf-8")
        ).hexdigest()

        assert record.text_norm_hash == expected
        assert len(record.text_norm_hash) == 64
