from __future__ import annotations

import pytest

from app.services.report.community_member_count_provider import (
    resolve_community_member_count,
)


@pytest.mark.asyncio
async def test_resolve_community_member_count_prefers_db_value() -> None:
    async def _fetch_db(_community: str) -> int | None:
        return 1_200_000

    member_count = await resolve_community_member_count(
        "r/startups",
        fetch_db_member_count=_fetch_db,
        configured_member_counts={"r/startups": 1_500_000},
    )

    assert member_count == 1_200_000


@pytest.mark.asyncio
async def test_resolve_community_member_count_falls_back_to_config_on_db_error() -> None:
    async def _fetch_db(_community: str) -> int | None:
        raise RuntimeError("DB error")

    member_count = await resolve_community_member_count(
        "r/startups",
        fetch_db_member_count=_fetch_db,
        configured_member_counts={"r/startups": 1_500_000},
    )

    assert member_count == 1_500_000


@pytest.mark.asyncio
async def test_resolve_community_member_count_falls_back_to_default() -> None:
    async def _fetch_db(_community: str) -> int | None:
        return None

    member_count = await resolve_community_member_count(
        "r/unknown",
        fetch_db_member_count=_fetch_db,
        configured_member_counts={},
    )

    assert member_count == 100_000
