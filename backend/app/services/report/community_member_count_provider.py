from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable


logger = logging.getLogger(__name__)


async def resolve_community_member_count(
    community_name: str,
    *,
    fetch_db_member_count: Callable[[str], Awaitable[int | None]],
    configured_member_counts: dict[str, int],
) -> int:
    """Resolve community member count from DB first, then config, then default."""
    try:
        member_count = await fetch_db_member_count(community_name)
        if member_count is not None and member_count > 0:
            logger.debug(
                "Using DB member count for %s: %s",
                community_name,
                f"{member_count:,}",
            )
            return member_count
    except Exception as exc:
        logger.warning(
            "Failed to fetch member count from DB for %s: %s",
            community_name,
            exc,
        )

    config_count = configured_member_counts.get(community_name.lower())
    if config_count:
        logger.debug(
            "Using config member count for %s: %s",
            community_name,
            f"{config_count:,}",
        )
        return config_count

    logger.debug("Using default member count for %s: 100,000", community_name)
    return 100_000


__all__ = ["resolve_community_member_count"]
