from __future__ import annotations

import hashlib

from app.services.hotpost.cache import build_hotpost_cache_key, get_hotpost_cache_ttl_seconds


def _hash(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:8]


def test_build_hotpost_cache_key_normalizes_and_sorts() -> None:
    query = "  Adobe吐槽  "
    subs = ["graphic_design", "r/Adobe"]
    expected_query = _hash("adobe吐槽")
    expected_subs = _hash(",".join(["r/adobe", "r/graphic_design"]))
    key = build_hotpost_cache_key(query, "rant", subs)
    assert key == f"reddit_hot:rant:{expected_query}:{expected_subs}"


def test_get_hotpost_cache_ttl_seconds_defaults(monkeypatch) -> None:
    monkeypatch.delenv("CACHE_TTL_TRENDING", raising=False)
    monkeypatch.delenv("CACHE_TTL_RANT", raising=False)
    monkeypatch.delenv("CACHE_TTL_OPPORTUNITY", raising=False)

    assert get_hotpost_cache_ttl_seconds("trending") == 1800
    assert get_hotpost_cache_ttl_seconds("rant") == 7200
    assert get_hotpost_cache_ttl_seconds("opportunity") == 3600
