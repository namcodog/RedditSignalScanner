from __future__ import annotations

import pytest

from app.schemas.hotpost import HotpostSearchRequest


def test_subreddits_limit_allows_10() -> None:
    subreddits = [f"r/test{i}" for i in range(10)]
    req = HotpostSearchRequest(query="test", subreddits=subreddits)
    assert req.subreddits is not None
    assert len(req.subreddits) == 10


def test_subreddits_limit_rejects_11() -> None:
    subreddits = [f"r/test{i}" for i in range(11)]
    with pytest.raises(ValueError):
        HotpostSearchRequest(query="test", subreddits=subreddits)
