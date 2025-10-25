from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, List

import json

import pytest

from app.services.community_pool_loader import CommunityPoolLoader


# ---------------------------- Fakes/Stubs ----------------------------
@dataclass
class Row:
    name: str
    tier: str = "mid"
    priority: str = "medium"
    categories: dict[str, Any] | list[str] | None = None
    description_keywords: dict[str, Any] | None = None
    daily_posts: int = 0
    avg_comment_length: int = 0
    quality_score: float = 0.5
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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


@pytest.mark.asyncio
async def test_load_seed_communities_clears_soft_delete(tmp_path: Path) -> None:
    deleted_time = datetime.now(timezone.utc)
    existing = Row(
        name="r/test",
        tier="medium",
        priority="low",
        categories={"general": True},
        description_keywords={"automation": 1.0},
        daily_posts=10,
        avg_comment_length=80,
        quality_score=0.3,
        is_active=False,
        deleted_at=deleted_time,
        deleted_by="dead-beef",
    )

    script = [[existing]]
    session = FakeSession(script=script)

    seed_payload = {
        "communities": [
            {
                "name": "r/test",
                "tier": "high",
                "priority": "high",
                "categories": {"general": 1},
                "description_keywords": {"automation": 1.0},
                "estimated_daily_posts": 25,
                "avg_comment_length": 120,
                "quality_score": 0.9,
                "is_active": True,
            }
        ]
    }
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

    loader = CommunityPoolLoader(session, seed_path=seed_file)  # type: ignore[arg-type]
    stats = await loader.load_seed_communities()

    assert stats["loaded"] == 0
    assert stats["updated"] == 1
    assert existing.deleted_at is None
    assert existing.deleted_by is None
    assert existing.is_active is True


@pytest.mark.asyncio
async def test_load_seed_communities_updates_timestamp(tmp_path: Path) -> None:
    initial_updated = datetime.now(timezone.utc) - timedelta(days=1)
    existing = Row(
        name="r/productivity",
        tier="medium",
        priority="medium",
        categories={"general": True},
        description_keywords={"automation": 1.0},
        daily_posts=12,
        avg_comment_length=60,
        quality_score=0.6,
        is_active=True,
        updated_at=initial_updated,
    )

    script = [[existing]]
    session = FakeSession(script=script)

    seed_payload = {
        "communities": [
            {
                "name": "r/productivity",
                "tier": "high",
                "priority": "high",
                "categories": {"general": 1},
                "description_keywords": {"automation": 1.0},
                "estimated_daily_posts": 30,
                "avg_comment_length": 90,
                "quality_score": 0.9,
                "is_active": True,
            }
        ]
    }
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

    loader = CommunityPoolLoader(session, seed_path=seed_file)  # type: ignore[arg-type]
    await loader.load_seed_communities()

    assert existing.updated_at > initial_updated
