import pytest
from sqlalchemy import select

from app.models.discovered_community import DiscoveredCommunity
from app.services.hotpost.repository import maybe_discover_community


@pytest.mark.asyncio
async def test_maybe_discover_community_normalizes_name(db_session) -> None:
    await maybe_discover_community(
        db_session,
        subreddit="AI_Tools_Land",
        evidence_count=5,
        query="AI tools",
        keywords=["AI", "tools"],
    )

    result = await db_session.execute(
        select(DiscoveredCommunity).where(
            DiscoveredCommunity.name == "r/ai_tools_land"
        )
    )
    assert result.scalar_one_or_none() is not None
