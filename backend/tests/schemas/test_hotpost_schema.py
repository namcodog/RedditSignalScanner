from __future__ import annotations

import pytest

from app.schemas.hotpost import HotpostSearchRequest


def test_hotpost_search_request_normalization() -> None:
    req = HotpostSearchRequest(
        query="  Robo vacuum ",
        mode="RANT",
        time_filter="Month",
        subreddits=["r/Test", "  foo  ", ""],
        limit=30,
    )

    assert req.query == "Robo vacuum"
    assert req.mode == "rant"
    assert req.time_filter == "month"
    assert req.subreddits == ["r/test", "r/foo"]


def test_hotpost_search_request_limit_bounds() -> None:
    with pytest.raises(ValueError):
        HotpostSearchRequest(query="test", limit=0)
    with pytest.raises(ValueError):
        HotpostSearchRequest(query="test", limit=101)


def test_hotpost_search_request_subreddit_limit() -> None:
    subs = [f"r/test{i}" for i in range(6)]
    with pytest.raises(ValueError):
        HotpostSearchRequest(query="test", subreddits=subs)
