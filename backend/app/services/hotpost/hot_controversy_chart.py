from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from threading import Thread
from typing import Optional, Any

from app.services.hotpost.hot_comment_sample import collect_hot_comment_sample
from app.services.hotpost.hot_controversy_llm import build_hot_controversy_result
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile
from app.services.infrastructure.reddit_collect_client import build_collect_reddit_client


def enrich_hot_controversy_chart(card: dict[str, Any]) -> dict[str, Any]:
    lane = str(card.get("lane") or "")
    card_type = str(card.get("card_type") or "")
    if lane != "hot" or card_type != "validate":
        return card
    return card if isinstance(card.get("controversy_chart"), dict) else card


def refresh_hot_controversy_cards_sync(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(refresh_hot_controversy_cards(cards))

    result: list[list[dict[str, Any]]] = []
    errors: list[BaseException] = []

    def _run_in_thread() -> None:
        try:
            result.append(asyncio.run(refresh_hot_controversy_cards(cards)))
        except BaseException as exc:
            errors.append(exc)

    thread = Thread(target=_run_in_thread, daemon=True)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    if not result:
        raise RuntimeError("refresh_hot_controversy_cards_sync did not return a result")
    return result[0]


async def refresh_hot_controversy_cards(
    cards: list[dict[str, Any]],
    *,
    reddit_client:Optional[ Any] = None,
    llm_client:Optional[ Any] = None,
    llm_model:Optional[ str] = None,
) -> list[dict[str, Any]]:
    refreshed: list[dict[str, Any]] = []
    async with _managed_reddit_client(reddit_client) as reddit:
        for card in cards:
            if str(card.get("lane") or "") != "hot" or str(card.get("card_type") or "") != "validate":
                refreshed.append(card)
                continue
            sample = await collect_hot_comment_sample(card, reddit_client=reddit)
            chart, meta = await build_hot_controversy_result(
                card=card,
                sample=sample,
                llm_client=llm_client,
                llm_model=llm_model,
            )
            next_card = dict(card)
            next_card["controversy_meta"] = meta
            if chart is not None:
                next_card["controversy_chart"] = chart
            refreshed.append(next_card)
    return refreshed


@asynccontextmanager
async def _managed_reddit_client(reddit_client:Optional[ Any]):
    if reddit_client is not None:
        yield reddit_client
        return
    collect_defaults = get_supply_collect_profile("safe")
    async with build_collect_reddit_client(
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=max(1, int(collect_defaults.get("api_max_concurrency") or 2)),
        low_quota_remaining_threshold=int(collect_defaults.get("low_quota_remaining_threshold") or 12),
        low_quota_cooldown_seconds=float(collect_defaults.get("low_quota_cooldown_seconds") or 20),
        stop_comment_fetch_below_remaining=int(collect_defaults.get("stop_comment_fetch_below_remaining") or 18),
        max_consecutive_rate_limit_errors=int(collect_defaults.get("max_consecutive_rate_limit_errors") or 3),
    ) as client:
        yield client


__all__ = [
    "enrich_hot_controversy_chart",
    "refresh_hot_controversy_cards",
    "refresh_hot_controversy_cards_sync",
]
