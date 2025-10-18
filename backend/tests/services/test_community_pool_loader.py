"""Unit tests for CommunityPoolLoader service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.community_pool_loader import CommunityPoolLoader


@pytest.mark.asyncio
async def test_loader_imports() -> None:
    """Test that loader can be imported."""
    assert CommunityPoolLoader is not None


@pytest.mark.asyncio
async def test_seed_file_validation(tmp_path: Path) -> None:
    """Test seed file validation."""
    from unittest.mock import AsyncMock
    
    mock_db = AsyncMock()
    seed_file = tmp_path / "seed.json"
    loader = CommunityPoolLoader(db=mock_db, seed_path=seed_file)
    
    # Test file not found
    with pytest.raises(FileNotFoundError):
        await loader.load_seed_communities()
    
    # Test invalid JSON
    seed_file.write_text("invalid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        await loader.load_seed_communities()
    
    # Test no communities
    seed_file.write_text(json.dumps({"communities": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="No communities found"):
        await loader.load_seed_communities()


class _FakeExecResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return _FakeExecResult()

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_default_seed_loads_full_community_expansion() -> None:
    """确保默认种子文件会导入 200 个社区。"""
    session = _FakeSession()
    loader = CommunityPoolLoader(db=session)  # type: ignore[arg-type]

    stats = await loader.load_seed_communities()

    assert stats["total_in_file"] == 200
    assert len(session.added) == 200
    assert session.committed is True
