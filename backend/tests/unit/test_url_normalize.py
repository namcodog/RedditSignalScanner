from app.utils.url import normalize_reddit_url


def test_normalize_prefers_full_reddit_url():
    u = normalize_reddit_url(url="https://www.reddit.com/r/test/comments/abc")
    assert u.startswith("https://www.reddit.com/r/test/")


def test_normalize_from_relative_url():
    u = normalize_reddit_url(url="/r/test/comments/abc")
    assert u == "https://www.reddit.com/r/test/comments/abc"


def test_normalize_from_permalink_relative():
    u = normalize_reddit_url(permalink="/r/foo/comments/xyz")
    assert u == "https://www.reddit.com/r/foo/comments/xyz"


def test_fallback_to_non_reddit_full_url_when_no_permalink():
    u = normalize_reddit_url(url="https://example.com/post")
    assert u == "https://example.com/post"


def test_final_fallback():
    u = normalize_reddit_url()
    assert u == "https://www.reddit.com"

