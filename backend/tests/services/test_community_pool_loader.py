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
