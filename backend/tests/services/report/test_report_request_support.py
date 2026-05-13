from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.report.report_request_support import (
    finalize_report_request,
    resolve_cached_report_payload,
)


@pytest.mark.asyncio
async def test_resolve_cached_report_payload_hits_only_when_timestamp_matches() -> None:
    generated_at = datetime.now(timezone.utc)
    payload = SimpleNamespace(generated_at=generated_at)
    cache_get = AsyncMock(return_value=payload)

    hit = await resolve_cached_report_payload(
        cache_get=cache_get,
        cache_key="report:key",
        generated_at=generated_at,
        task_id=uuid4(),
    )
    miss = await resolve_cached_report_payload(
        cache_get=cache_get,
        cache_key="report:key",
        generated_at=datetime.now(timezone.utc),
        task_id=uuid4(),
    )

    assert hit is payload
    assert miss is None


@pytest.mark.asyncio
async def test_finalize_report_request_persists_structured_and_sets_cache() -> None:
    payload = SimpleNamespace(canonical_report_json={"battlefields": [{"name": "r/demo"}]})
    analysis = SimpleNamespace()
    cache_set = AsyncMock()
    persist = AsyncMock(return_value=True)

    await finalize_report_request(
        payload=payload,
        analysis=analysis,
        cache_key="report:key",
        cache_set=cache_set,
        persist_report_structured=persist,
        task_id=uuid4(),
        task_status="completed",
    )

    persist.assert_awaited_once_with(analysis, {"battlefields": [{"name": "r/demo"}]})
    cache_set.assert_awaited_once_with("report:key", payload)
