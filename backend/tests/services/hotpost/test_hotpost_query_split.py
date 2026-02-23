from __future__ import annotations

from app.services.hotpost.service import HotpostService


def test_split_search_query_keeps_short_query() -> None:
    query = "paint by numbers kit"
    parts = HotpostService._split_search_queries(query, max_chars=50)
    assert parts == [query]


def test_split_search_query_splits_or_chunks() -> None:
    query = "alpha OR beta OR gamma OR delta"
    parts = HotpostService._split_search_queries(query, max_chars=12)
    assert len(parts) >= 2
    assert all(len(p) <= 12 for p in parts)


def test_split_search_query_splits_long_text() -> None:
    query = "this is a very long query that should be split into chunks"
    parts = HotpostService._split_search_queries(query, max_chars=20)
    assert len(parts) >= 2
    assert all(len(p) <= 20 for p in parts)
