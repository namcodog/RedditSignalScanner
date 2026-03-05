from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostRaw
from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis import analysis_engine as analysis_engine_module
from app.services.analysis.analysis_engine import run_analysis
from app.services.analysis.sample_guard import SampleCheckResult
from app.services.crawl.data_collection import CollectionResult
from app.services.infrastructure.reddit_client import RedditPost


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.asyncio
async def test_run_analysis_uses_comments_as_pain_evidence_and_counts_authors(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _pass_guard(**_: object) -> SampleCheckResult:
        return SampleCheckResult(
            hot_count=900,
            cold_count=700,
            combined_count=1600,
            shortfall=0,
            remaining_shortfall=0,
            supplemented=False,
            supplement_posts=[],
        )

    monkeypatch.setattr(analysis_engine_module.sample_guard, "check_sample_size", _pass_guard)

    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    # Avoid demo-post injection noise for this test.
    monkeypatch.setattr(analysis_engine_module, "_backfill_cache_misses", lambda collected, _kw: collected)

    now = datetime.now(timezone.utc)
    subreddit = "r/shopify"
    task_id = uuid4()

    # Seed community_pool row (run_analysis prefers DB pool)
    created_pool = False
    existing = await db_session.execute(select(CommunityPool).where(CommunityPool.name == subreddit))
    pool = existing.scalar_one_or_none()
    if pool is None:
        created_pool = True
        pool = CommunityPool(
            name=subreddit,
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="high",
            is_active=True,
            is_blacklisted=False,
        )
        db_session.add(pool)
        await db_session.flush()

    # Seed one post in cold storage so comment query can link by source_post_id.
    source_post_id = f"t3_comment_pain_{task_id.hex[:12]}"
    post = PostRaw(
        source="reddit",
        source_post_id=source_post_id,
        version=1,
        created_at=now,
        fetched_at=now,
        valid_from=now,
        title="Shopify ads attribution question",
        body="Need advice on Shopify conversion tracking and ROAS measurement.",
        subreddit=subreddit,
        community_id=pool.id,
        score=50,
        num_comments=2,
        is_current=True,
        author_name="poster_1",
    )
    db_session.add(post)
    await db_session.flush()

    # Insert a high-signal comment: contains pain words, but also on-topic keywords.
    await db_session.execute(
        text(
            """
            INSERT INTO comments (
                reddit_comment_id, source, source_post_id, post_id, subreddit,
                depth, body, created_utc, score, is_submitter, edited, captured_at,
                business_pool, author_name
            ) VALUES (
                :reddit_comment_id, 'reddit', :source_post_id, :post_id, :subreddit,
                0, :body, :created_utc, 99, false, false, :captured_at,
                'lab', :author_name
            )
            """
        ),
        {
            "reddit_comment_id": f"t1_{task_id.hex[:18]}_pain",
            "source_post_id": source_post_id,
            "post_id": int(post.id),
            "subreddit": subreddit,
            "body": "My ROAS is terrible and I'm frustrated with ad spend on my Shopify store.",
            "created_utc": now,
            "captured_at": now,
            "author_name": "commenter_1",
        },
    )
    await db_session.commit()

    # Grab the internal comment id (facts_v2 evidence_quote_ids uses comment.id, not reddit_comment_id).
    comment_id = await db_session.scalar(
        text("SELECT id FROM comments WHERE reddit_comment_id = :rid"),
        {"rid": f"t1_{task_id.hex[:18]}_pain"},
    )
    assert comment_id is not None
    expected_quote_id = str(comment_id)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(self, communities, *, limit_per_subreddit: int = 100) -> CollectionResult:  # noqa: ARG002
            # Shopify profile 是窄题：run_analysis 需要 >=10 条（去重后）才会进入 facts_v2 阶段，
            # 否则会被 topic-level insufficient_samples 早退掉，拿不到评论证据链。
            posts = [
                RedditPost(
                    id=source_post_id,
                    title="Shopify ads attribution question",
                    selftext="Need advice on Shopify conversion tracking and ROAS measurement.",
                    score=50,
                    num_comments=2,
                    created_utc=1.0,
                    subreddit=subreddit,
                    author="poster_1",
                    url=f"https://reddit.com/{subreddit}/{source_post_id}",
                    permalink=f"/{subreddit}/{source_post_id}",
                )
            ]
            context_terms = [
                "ROAS",
                "CPC",
                "CTR",
                "CPM",
                "CPA",
                "campaign",
                "pixel",
                "attribution",
                "conversion",
                "retargeting",
                "creative",
                "tracking",
            ]
            markers = [
                "aardvark",
                "buffalo",
                "cheetah",
                "dolphin",
                "elephant",
                "flamingo",
                "gorilla",
                "hyena",
                "iguana",
                "jaguar",
                "koala",
            ]
            for idx in range(11):
                uniq = uuid4().hex
                term = context_terms[idx % len(context_terms)]
                marker = markers[idx % len(markers)]
                pid = f"t3_{uniq[:12]}{idx:02d}"
                posts.append(
                    RedditPost(
                        id=pid,
                        title=f"Shopify {term} setup question ({marker}) ({uniq})",
                        selftext=(
                            f"Need advice on Shopify {term} tracking and conversion setup. ({marker}) ({uniq})"
                        ),
                        score=49 - idx,
                        num_comments=1,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"poster_{idx + 2}",
                        url=f"https://reddit.com/{subreddit}/{pid}",
                        permalink=f"/{subreddit}/{pid}",
                    )
                )
            posts_by_subreddit = {subreddit: posts}
            return CollectionResult(
                total_posts=len(posts),
                cache_hits=1,
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=set(posts_by_subreddit.keys()),
            )

        async def close(self) -> None:
            return None

    result = await run_analysis(
        TaskSummary(
            id=task_id,
            status=TaskStatus.PENDING,
            product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
            topic_profile_id="shopify_ads_conversion_v1",
            created_at=now,
            updated_at=now,
        ),
        data_collection=StubService(),
    )

    facts = result.sources.get("facts_v2_package")
    assert isinstance(facts, dict)
    signals = facts.get("business_signals") or {}
    pains = signals.get("high_value_pains") or []
    assert pains, "Expected pain signals to be extracted from comments when posts are neutral"

    first = pains[0]
    evidence = first.get("evidence_quote_ids") or []
    assert expected_quote_id in [str(x) for x in evidence], "Expected comment id to be used as evidence_quote_id"
    metrics = first.get("metrics") or {}
    assert int(metrics.get("unique_authors") or 0) >= 1

    # cleanup
    await db_session.execute(text("DELETE FROM comments WHERE source_post_id = :pid"), {"pid": source_post_id})
    await db_session.execute(delete(PostRaw).where(PostRaw.source_post_id == source_post_id))
    if created_pool:
        await db_session.execute(delete(CommunityPool).where(CommunityPool.id == pool.id))
    await db_session.commit()
