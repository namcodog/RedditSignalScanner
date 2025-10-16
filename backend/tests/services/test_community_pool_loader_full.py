from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List

import pytest

from app.services.community_pool_loader import CommunityPoolLoader


# ---------------------------- Fakes/Stubs ----------------------------
@dataclass
class Row:
    name: str
    tier: str = "mid"
    priority: str = "medium"
    categories: list[str] | None = None
    description_keywords: dict[str, Any] | None = None
    daily_posts: int = 0
    avg_comment_length: int = 0
    quality_score: float = 0.5
    is_active: bool = True


class _ScalarResult:
    def __init__(self, items: Iterable[Any]) -> None:
        self._items = list(items)

    def all(self) -> List[Any]:
        return list(self._items)

    def one_or_none(self) -> Any | None:
        return self._items[0] if self._items else None


class _ExecResult:
    def __init__(self, items: Iterable[Any]) -> None:
        self._items = list(items)

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._items)

    def scalar_one_or_none(self) -> Any | None:
        return self._items[0] if self._items else None


class FakeSession:
    def __init__(self, script: list[list[Any]] | None = None) -> None:
        self.script = script or []
        self.added: list[Any] = []
        self.committed = False
        self._cursor = 0

    async def execute(self, _stmt: Any) -> _ExecResult:  # noqa: ARG002 - unused
        # return next scripted result list
        if self._cursor < len(self.script):
            items = self.script[self._cursor]
            self._cursor += 1
        else:
            items = []
        return _ExecResult(items)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True


# ------------------------------ Tests -------------------------------
@pytest.mark.asyncio
async def test_get_pool_stats_counts_and_averages() -> None:
    # Arrange: 3 communities with mixed priority/active
    rows = [
        Row(name="a", priority="high", is_active=True, quality_score=0.8),
        Row(name="b", priority="medium", is_active=False, quality_score=0.6),
        Row(name="c", priority="low", is_active=True, quality_score=0.4),
    ]
    db = FakeSession(script=[rows])
    loader = CommunityPoolLoader(db)  # type: ignore[arg-type]

    # Act
    stats = await loader.get_pool_stats()

    # Assert
    assert stats["total_communities"] == 3
    assert stats["active_communities"] == 2
    assert stats["inactive_communities"] == 1
    assert stats["high_priority"] == 1
    assert stats["medium_priority"] == 1
    assert stats["low_priority"] == 1
    assert stats["avg_quality_score"] == pytest.approx((0.8 + 0.6 + 0.4) / 3, rel=1e-3)


@pytest.mark.asyncio
async def test_initialize_community_cache_creates_entries() -> None:
    # Arrange: No existing cache, pool provides priority info
    community_names = ["alpha", "beta"]
    # script executes per community: [cache_lookup], [pool_lookup]
    script = [
        [None], [Row(name="alpha", priority="high", quality_score=0.9)],
        [None], [Row(name="beta", priority="medium", quality_score=0.7)],
    ]
    db = FakeSession(script=script)
    loader = CommunityPoolLoader(db)  # type: ignore[arg-type]

    # Act
    stats = await loader.initialize_community_cache(communities=community_names)

    # Assert
    assert stats["total_communities"] == 2
    assert stats["initialized"] == 2
    assert stats["skipped"] == 0
    # ensure objects were added and committed
    assert db.committed is True
    assert len(db.added) == 2

