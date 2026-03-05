from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.comment import ContentLabel, ContentType, Category, Aspect
from app.services.analysis.ps_ratio import compute_ps_ratio_from_labels


@pytest.mark.asyncio
async def test_compute_ps_ratio_from_labels_basic() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        subreddit = f"test_ps_basic_{uuid.uuid4().hex[:8]}"
        cid1 = f"c_ps_1_{uuid.uuid4().hex[:8]}"
        cid2 = f"c_ps_2_{uuid.uuid4().hex[:8]}"
        # Insert two comments
        await session.execute(
            text(
                """
                INSERT INTO comments (reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc)
                VALUES (:cid1,'reddit','p1',:sub,0,'pain about subscription',:ts),
                       (:cid2,'reddit','p1',:sub,0,'solution tip',:ts)
                """
            ),
            {"ts": now, "cid1": cid1, "cid2": cid2, "sub": subreddit},
        )
        # fetch their ids
        rows = await session.execute(
            text(
                "SELECT id, reddit_comment_id FROM comments WHERE reddit_comment_id IN (:cid1, :cid2) ORDER BY reddit_comment_id"
            ),
            {"cid1": cid1, "cid2": cid2},
        )
        ids = {r[1]: int(r[0]) for r in rows.fetchall()}
        # label one as pain and the other as solution
        await session.merge(
            ContentLabel(
                content_type=ContentType.COMMENT.value,
                content_id=ids[cid1],
                category=Category.PAIN.value,
                aspect=Aspect.SUBSCRIPTION.value,
                confidence=90,
            )
        )
        await session.merge(
            ContentLabel(
                content_type=ContentType.COMMENT.value,
                content_id=ids[cid2],
                category=Category.SOLUTION.value,
                aspect=Aspect.OTHER.value,
                confidence=80,
            )
        )
        await session.commit()

        ratio = await compute_ps_ratio_from_labels(
            session, since_days=365, subreddits=[subreddit]
        )
        assert ratio is not None
        assert abs(ratio - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_compute_ps_ratio_excludes_noise_comments() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        subreddit = f"test_noise_ps_{uuid.uuid4().hex[:8]}"
        biz_cid = f"c_ps_biz_{uuid.uuid4().hex[:8]}"
        noise_cid = f"c_ps_noise_{uuid.uuid4().hex[:8]}"
        await session.execute(
            text(
                """
                INSERT INTO comments (reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc, business_pool)
                VALUES (:biz_cid,'reddit','p2',:sub,0,'pain',:ts,'lab'),
                       (:noise_cid,'reddit','p2',:sub,0,'solution',:ts,'noise')
                """
            ),
            {"ts": now, "sub": subreddit, "biz_cid": biz_cid, "noise_cid": noise_cid},
        )
        rows = await session.execute(
            text(
                "SELECT id, reddit_comment_id FROM comments WHERE reddit_comment_id IN (:biz_cid, :noise_cid)"
            ),
            {"biz_cid": biz_cid, "noise_cid": noise_cid},
        )
        ids = {str(r[1]): int(r[0]) for r in rows.fetchall()}

        # Business comment: 1 pain
        await session.merge(
            ContentLabel(
                content_type=ContentType.COMMENT.value,
                content_id=ids[biz_cid],
                category=Category.PAIN.value,
                aspect=Aspect.SUBSCRIPTION.value,
                confidence=90,
            )
        )

        # Noise comment: 2 solutions (should be excluded from ratio)
        await session.merge(
            ContentLabel(
                content_type=ContentType.COMMENT.value,
                content_id=ids[noise_cid],
                category=Category.SOLUTION.value,
                aspect=Aspect.OTHER.value,
                confidence=80,
            )
        )
        await session.merge(
            ContentLabel(
                content_type=ContentType.COMMENT.value,
                content_id=ids[noise_cid],
                category=Category.SOLUTION.value,
                aspect=Aspect.OTHER.value,
                confidence=80,
            )
        )
        await session.commit()

        ratio = await compute_ps_ratio_from_labels(session, since_days=365, subreddits=[subreddit])
        assert ratio is not None
        assert abs(ratio - 1.0) < 1e-6
