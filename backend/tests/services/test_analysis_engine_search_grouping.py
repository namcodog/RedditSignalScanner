from __future__ import annotations

from app.services.analysis_engine import CommunityProfile, _group_search_posts_by_selected_subreddit
from app.services.reddit_client import RedditPost


def test_group_search_posts_normalizes_subreddit_names() -> None:
    selected = [
        CommunityProfile(
            name="r/Shopify",
            categories=("profile_seed",),
            description_keywords=("shopify",),
            daily_posts=10,
            avg_comment_length=50,
            cache_hit_rate=0.0,
        )
    ]
    search_posts = [
        RedditPost(
            id="t3_demo",
            title="Shopify ROAS dropped",
            selftext="Need help with ads",
            score=10,
            num_comments=5,
            created_utc=0.0,
            subreddit="Shopify",
            author="demo",
            url="",
            permalink="",
        )
    ]

    grouped = _group_search_posts_by_selected_subreddit(
        search_posts=search_posts,
        selected=selected,
    )
    assert "r/shopify" in grouped
    assert len(grouped["r/shopify"]) == 1
