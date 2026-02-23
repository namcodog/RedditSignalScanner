from __future__ import annotations

from app.schemas.hotpost import HotpostSearchRequest
from app.services.hotpost.service import HotpostService


def test_default_time_filter_trending_is_all() -> None:
    req = HotpostSearchRequest(query="test query")
    assert HotpostService._resolve_time_filter("trending", req) == "all"
