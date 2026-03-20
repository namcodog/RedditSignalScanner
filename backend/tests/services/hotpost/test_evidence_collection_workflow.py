from __future__ import annotations

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.evidence_collection_workflow import (
    HotpostEvidenceCollectionDeps,
    HotpostEvidenceCollectionInput,
    collect_hotpost_evidence,
)
from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.infrastructure.reddit_client import RedditPost


def _reddit_post(*, post_id: str, title: str, body: str, subreddit: str) -> RedditPost:
    return RedditPost(
        id=post_id,
        title=title,
        selftext=body,
        score=12,
        num_comments=3,
        created_utc=0.0,
        subreddit=subreddit,
        author="user",
        url=f"https://reddit.com/{post_id}",
        permalink=f"/r/{subreddit}/comments/{post_id}",
    )


def _hotpost(post: RedditPost, *, rank: int, signals: dict[str, list[str]]) -> Hotpost:
    return Hotpost(
        rank=rank,
        id=post.id,
        title=post.title,
        body_preview=post.selftext[:100],
        score=post.score,
        num_comments=post.num_comments,
        heat_score=post.score + post.num_comments * 2,
        rant_score=10.0,
        rant_signals=[signal for group in signals.values() for signal in group],
        subreddit=post.subreddit,
        author=post.author,
        reddit_url=post.url,
        created_utc=post.created_utc,
        signals=[signal for group in signals.values() for signal in group],
        signal_score=10.0,
        top_comments=[],
    )


async def _noop_rate_budget(*_args: object, **_kwargs: object) -> None:
    return None


async def test_collect_hotpost_evidence_suggests_subreddits_and_builds_distribution() -> None:
    async def _search_subreddits(query: str, *, limit: int, include_nsfw: bool) -> list[dict[str, str]]:
        assert query == "robot vacuum"
        assert limit == 5
        assert include_nsfw is False
        return [{"name": "robotvacuums"}]

    async def _search_subreddit_posts(
        subreddit: str,
        query: str,
        *,
        sort: str,
        time_filter: str,
        max_posts: int,
        queue_tracker: object | None = None,
    ) -> tuple[list[RedditPost], int]:
        assert subreddit == "r/robotvacuums"
        assert query == "robot vacuum"
        assert sort == "top"
        assert time_filter == "month"
        assert max_posts == 30
        return (
            [
                _reddit_post(
                    post_id="p1",
                    title="Hidden gem robot vacuum",
                    body="This hidden gem works great.",
                    subreddit="r/robotvacuums",
                ),
                _reddit_post(
                    post_id="p2",
                    title="Love this vacuum",
                    body="A great robot vacuum for apartments.",
                    subreddit="r/robotvacuums",
                ),
            ],
            1,
        )

    async def _fetch_comments(post_id: str, *, queue_tracker: object | None = None) -> list[dict[str, object]]:
        return [
            {
                "name": f"t1_{post_id}",
                "author": "commenter",
                "body": "me too",
                "score": 5,
                "permalink": f"/r/robotvacuums/comments/{post_id}/_/{post_id}",
            }
        ]

    result = await collect_hotpost_evidence(
        workflow_input=HotpostEvidenceCollectionInput(
            request_query="robot vacuum",
            query_parts=["robot vacuum"],
            keywords=["robot", "vacuum"],
            mode="discovery",
            time_filter="month",
            sort="top",
            limit=10,
            requested_subreddits=None,
            suggest_subreddits_when_missing=True,
            enable_relevance_filter=True,
            max_posts_per_subreddit=30,
            notes=[],
        ),
        deps=HotpostEvidenceCollectionDeps(
            acquire_rate_budget=_noop_rate_budget,
            search_subreddits=_search_subreddits,
            search_subreddit_posts=_search_subreddit_posts,
            search_posts=None,
            fetch_comments=_fetch_comments,
            select_signals=lambda _mode, _text: {"positive": ["hidden gem"]},
            sentiment_label=lambda _mode, _text, _signals: "positive",
            build_post=_hotpost,
            build_pain_points=lambda _posts, _categories: [],
            confidence_level=lambda evidence_count: "low" if evidence_count < 10 else "medium",
            lexicon=load_default_hotpost_keywords(),
        ),
    )

    assert result.subreddits == ["r/robotvacuums"]
    assert result.api_calls == 2
    assert result.raw_posts == 2
    assert result.filtered_posts == 2
    assert result.relevance_filtered == 0
    assert result.community_distribution == {"r/robotvacuums": "100%"}
    assert len(result.top_posts) == 2
    assert len(result.all_comments) == 2
    assert result.sentiment_overview["positive"] == 1.0
    assert result.confidence == "low"


async def test_collect_hotpost_evidence_filters_low_relevance_opportunity_posts() -> None:
    async def _search_subreddit_posts(
        subreddit: str,
        query: str,
        *,
        sort: str,
        time_filter: str,
        max_posts: int,
        queue_tracker: object | None = None,
    ) -> tuple[list[RedditPost], int]:
        assert subreddit == "r/saas"
        assert query == "invoice automation"
        return (
            [
                _reddit_post(
                    post_id="p1",
                    title="Need invoice automation badly",
                    body="Invoice automation is still painful.",
                    subreddit="r/saas",
                ),
                _reddit_post(
                    post_id="p2",
                    title="Totally unrelated gardening post",
                    body="Tomatoes are growing well this season.",
                    subreddit="r/saas",
                ),
            ],
            1,
        )

    async def _fetch_comments(_post_id: str, *, queue_tracker: object | None = None) -> list[dict[str, object]]:
        return []

    result = await collect_hotpost_evidence(
        workflow_input=HotpostEvidenceCollectionInput(
            request_query="invoice automation",
            query_parts=["invoice automation"],
            keywords=["invoice", "automation"],
            mode="opportunity",
            time_filter="year",
            sort="top",
            limit=10,
            requested_subreddits=["r/saas"],
            suggest_subreddits_when_missing=False,
            enable_relevance_filter=True,
            max_posts_per_subreddit=30,
            notes=[],
        ),
        deps=HotpostEvidenceCollectionDeps(
            acquire_rate_budget=_noop_rate_budget,
            search_subreddits=None,
            search_subreddit_posts=_search_subreddit_posts,
            search_posts=None,
            fetch_comments=_fetch_comments,
            select_signals=lambda _mode, _text: {"need": ["automation"]},
            sentiment_label=lambda _mode, _text, _signals: "neutral",
            build_post=_hotpost,
            build_pain_points=lambda _posts, _categories: [],
            confidence_level=lambda evidence_count: "low" if evidence_count < 10 else "medium",
            lexicon=load_default_hotpost_keywords(),
        ),
    )

    assert result.raw_posts == 2
    assert result.filtered_posts == 1
    assert result.relevance_filtered == 1
    assert len(result.top_posts) == 1
    assert result.top_posts[0].id == "p1"
    assert result.community_distribution == {"r/saas": "100%"}
