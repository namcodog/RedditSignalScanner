from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import PendingCommunity
from app.services import community_discovery
from app.services.community_discovery import CommunityDiscoveryService


class _StubRedditClient:
    async def search_posts(self, *args, **kwargs):  # pragma: no cover - not used here
        raise NotImplementedError


class _FrozenDateTime:
    def __init__(self, frozen: datetime) -> None:
        self._frozen = frozen

    def now(self, tz: timezone | None = None) -> datetime:
        if tz is None:
            return self._frozen
        return self._frozen.astimezone(tz)


@pytest.mark.asyncio
async def test_record_discoveries_updates_timestamp_for_existing_pending_community(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reddit_client = _StubRedditClient()
    service = CommunityDiscoveryService(db_session, reddit_client)

    past = datetime.now(timezone.utc) - timedelta(days=2)
    pending = PendingCommunity(
        name="r/testpending",
        discovered_from_keywords={"keywords": ["ai"], "mention_count": 1},
        discovered_count=1,
        first_discovered_at=past,
        last_discovered_at=past,
        status="pending",
        discovered_from_task_id=None,
    )
    # 手动设置历史更新时间，便于断言变化
    pending.updated_at = past
    db_session.add(pending)
    await db_session.commit()

    communities: Dict[str, int] = {"r/testpending": 3}
    keywords = ["ai"]

    expected_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        community_discovery,
        "datetime",
        _FrozenDateTime(expected_now),
        raising=False,
    )

    await service._record_discoveries(
        task_id=None,
        keywords=keywords,
        communities=communities,
    )

    await db_session.refresh(pending)
    assert pending.discovered_count == 4
    assert pending.updated_at is not None
    assert pending.updated_at == expected_now
