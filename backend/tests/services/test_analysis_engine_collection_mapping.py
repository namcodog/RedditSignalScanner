from __future__ import annotations

from app.services.analysis_engine import CommunityProfile, _collection_from_result
from app.services.data_collection import CollectionResult
from app.services.reddit_client import RedditPost


def test_collection_from_result_normalizes_profile_name_for_lookup() -> None:
    """大小写混用的社区名不应导致“明明有数据却当成空”。"""
    profile = CommunityProfile(
        name="r/PPC",
        categories=("test",),
        description_keywords=("ppc",),
        daily_posts=10,
        avg_comment_length=50,
        cache_hit_rate=1.0,
    )
    post = RedditPost(
        id="t3_demo",
        title="PPC help needed",
        selftext="ROAS dropped",
        score=1,
        num_comments=0,
        created_utc=1700000000.0,
        subreddit="ppc",
        author="tester",
        url="https://reddit.com",
        permalink="/r/ppc/comments/demo",
    )
    result = CollectionResult(
        total_posts=1,
        cache_hits=1,
        api_calls=0,
        cache_hit_rate=1.0,
        posts_by_subreddit={"r/ppc": [post]},
        cached_subreddits={"r/ppc"},
    )

    collected, hits, misses, total = _collection_from_result([profile], result)

    assert total == 1
    assert hits == 1
    assert misses == 0
    assert collected[0].posts and collected[0].posts[0]["id"] == "t3_demo"

