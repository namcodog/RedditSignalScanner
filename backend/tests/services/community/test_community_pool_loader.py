"""Unit tests for CommunityPoolLoader service."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.community.community_pool_loader import CommunityPoolLoader
from app.services.community import community_pool_loader as loader_module


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

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_default_seed_loads_full_community_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """确保 200 个种子社区能被完整导入。"""
    session = _FakeSession()
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(
        json.dumps(
            {
                "communities": [
                    {"name": f"r/test{i}", "tier": "medium"} for i in range(200)
                ]
            }
        ),
        encoding="utf-8",
    )
    loader = CommunityPoolLoader(db=session, seed_path=seed_file)  # type: ignore[arg-type]
    loader.top1000_file = tmp_path / "missing.json"

    async def _noop_replace(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(loader_module, "replace_community_category_map", _noop_replace)

    stats = await loader.load_seed_communities()

    assert stats["total_in_file"] == 200
    assert len(session.added) == 200
    assert session.committed is True


class _NoExistingRow:
    def scalar_one_or_none(self):
        return None


@pytest.mark.asyncio
async def test_load_seed_communities_fails_closed_when_whitelist_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(
        json.dumps({"communities": [{"name": "r/test", "tier": "medium"}]}),
        encoding="utf-8",
    )
    bad_whitelist = tmp_path / "community_whitelist.yaml"
    bad_whitelist.write_text("communities: [broken", encoding="utf-8")

    mock_db = AsyncMock()
    loader = CommunityPoolLoader(db=mock_db, seed_path=seed_file)
    loader.whitelist_file = bad_whitelist
    loader.top1000_file = tmp_path / "missing.json"

    monkeypatch.setenv("ENFORCE_COMMUNITY_WHITELIST", "1")
    with pytest.raises(ValueError, match="community whitelist"):
        await loader.load_seed_communities()


@pytest.mark.asyncio
async def test_load_seed_communities_ignores_deprecated_top1000(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(
        json.dumps({"communities": [{"name": "r/test", "tier": "medium"}]}),
        encoding="utf-8",
    )
    deprecated_top1000 = tmp_path / "top1000.json"
    deprecated_top1000.write_text("{invalid json", encoding="utf-8")

    mock_db = AsyncMock()
    mock_db.execute.return_value = _NoExistingRow()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def _noop_replace(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(loader_module, "replace_community_category_map", _noop_replace)
    monkeypatch.delenv("ENFORCE_COMMUNITY_WHITELIST", raising=False)

    loader = CommunityPoolLoader(db=mock_db, seed_path=seed_file)
    loader.top1000_file = deprecated_top1000

    stats = await loader.load_seed_communities()

    assert stats["degraded"] is False
    assert stats["top1000_status"] == "deprecated_ignored"
    assert stats["source_status"] == "loaded_full"
