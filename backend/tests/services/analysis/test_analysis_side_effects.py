from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis.analysis_side_effects import (
    record_discovered_communities_for_task,
)


@dataclass
class _StubProfile:
    name: str = "r/test"
    daily_posts: int = 10
    avg_comment_length: int = 20


@dataclass
class _StubCollectedCommunity:
    profile: _StubProfile
    posts: list[object]


@pytest.mark.asyncio
async def test_record_discovered_communities_skips_transient_task_context() -> None:
    task = TaskSummary(
        id=uuid4(),
        user_id=None,
        status=TaskStatus.PENDING,
        product_description="test product description",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await record_discovered_communities_for_task(
        task=task,
        collected=[_StubCollectedCommunity(profile=_StubProfile(), posts=[object()])],
        keywords=["test"],
    )

    assert result.status == "skipped"
    assert result.reason == "transient_task_context"


@pytest.mark.asyncio
async def test_record_discovered_communities_skips_non_persisted_task() -> None:
    task = TaskSummary(
        id=uuid4(),
        user_id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="test product description",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await record_discovered_communities_for_task(
        task=task,
        collected=[_StubCollectedCommunity(profile=_StubProfile(), posts=[object()])],
        keywords=["test"],
    )

    assert result.status == "skipped"
    assert result.reason == "task_not_persisted"
