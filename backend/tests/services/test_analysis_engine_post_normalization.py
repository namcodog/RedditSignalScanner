from app.services.analysis.analysis_engine import _reddit_post_to_dict
from app.services.infrastructure.reddit_client import RedditPost


def test_reddit_post_to_dict_handles_redditpost() -> None:
    post = RedditPost(
        id="abc",
        title="t",
        selftext="body text",
        score=12,
        num_comments=3,
        created_utc=0.0,
        subreddit="r/test",
        author="u1",
        url="https://example.com",
        permalink="/r/test/comments/abc",
    )

    result = _reddit_post_to_dict(post)

    assert result["id"] == "abc"
    assert result["summary"] == "body text"
    assert result["selftext"] == "body text"
    assert result["subreddit"] == "r/test"


def test_reddit_post_to_dict_handles_dict_payload() -> None:
    result = _reddit_post_to_dict(
        {
            "id": "xyz",
            "title": "hello",
            "selftext": "",
            "score": 1,
            "num_comments": 2,
            "subreddit": "r/demo",
        }
    )

    assert result["id"] == "xyz"
    assert result["summary"] == "hello"
    assert result["selftext"] == ""
    assert result["subreddit"] == "r/demo"


def test_reddit_post_to_dict_flattens_list_payload() -> None:
    payload = [
        {
            "id": "list1",
            "title": "list title",
            "selftext": "list body",
            "subreddit": "r/list",
        }
    ]

    result = _reddit_post_to_dict(payload)

    assert result["id"] == "list1"
    assert result["summary"] == "list body"
    assert result["selftext"] == "list body"
    assert result["subreddit"] == "r/list"
