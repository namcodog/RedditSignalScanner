from __future__ import annotations

from app.services.hotpost.detail_builder import (
    build_top_discovery_posts,
    build_top_rants,
    compute_need_urgency,
    compute_rant_intensity,
    extract_competitor_mentions,
)
from app.schemas.hotpost import Hotpost, HotpostComment


def _make_post(post_id: str, *, score: int, comments: int, signals: list[str], signal_score: float, why: str | None = None) -> Hotpost:
    return Hotpost(
        rank=1,
        id=post_id,
        title=f"Post {post_id}",
        body_preview="preview",
        score=score,
        num_comments=comments,
        heat_score=score + comments * 2,
        subreddit="r/test",
        author="user",
        reddit_url=f"https://www.reddit.com/r/test/comments/{post_id}",
        created_utc=0.0,
        signals=signals,
        signal_score=signal_score,
        why_relevant=why,
        top_comments=[
            HotpostComment(author="c1", body="me too", score=3, permalink="https://reddit.com"),
            HotpostComment(author="c2", body="agree", score=1, permalink="https://reddit.com"),
        ],
    )


def test_compute_rant_intensity() -> None:
    signal_groups = [
        {"strong": ["bad"], "medium": [], "weak": []},
        {"strong": [], "medium": ["meh"], "weak": []},
        {"strong": [], "medium": [], "weak": ["ok"]},
    ]
    intensity = compute_rant_intensity(signal_groups)
    assert round(intensity["strong"], 2) == 0.33
    assert round(intensity["medium"], 2) == 0.33
    assert round(intensity["weak"], 2) == 0.33


def test_compute_need_urgency() -> None:
    signal_groups = [
        {"unmet_need": ["need"], "seeking": []},
        {"unmet_need": [], "seeking": ["looking"]},
        {"unmet_need": [], "seeking": []},
    ]
    urgency = compute_need_urgency(signal_groups)
    assert round(urgency["urgent"], 2) == 0.33
    assert round(urgency["moderate"], 2) == 0.33
    assert round(urgency["casual"], 2) == 0.33


def test_build_top_rants() -> None:
    posts = [
        _make_post("a", score=10, comments=2, signals=["bad"], signal_score=50.0, why="important"),
        _make_post("b", score=5, comments=1, signals=["ok"], signal_score=10.0),
    ]
    top_rants = build_top_rants(posts)
    assert top_rants[0]["id"] == "a"
    assert top_rants[0]["rant_score"] == 50.0
    assert top_rants[0]["why_important"] == "important"


def test_build_top_discovery_posts() -> None:
    posts = [
        _make_post("a", score=10, comments=2, signals=["need"], signal_score=5.0, why="important"),
        _make_post("b", score=5, comments=1, signals=[], signal_score=1.0),
    ]
    top_posts = build_top_discovery_posts(posts)
    assert top_posts[0]["resonance_count"] >= 1
    assert top_posts[0]["why_important"] == "important"


def test_extract_competitor_mentions_from_titles() -> None:
    posts = [
        _make_post("a", score=10, comments=2, signals=["bad"], signal_score=5.0),
        _make_post("b", score=5, comments=1, signals=[], signal_score=1.0),
    ]
    posts[0].title = "Adobe vs Affinity comparison"
    posts[1].title = "Switched to Figma after years with Adobe"

    competitors = extract_competitor_mentions(posts, query="Adobe")
    names = {c["name"] for c in competitors}
    assert "Affinity" in names
    assert "Figma" in names
