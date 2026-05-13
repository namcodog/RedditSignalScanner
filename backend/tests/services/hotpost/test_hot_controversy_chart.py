from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_refresh_hot_controversy_cards_sync_runs_inside_existing_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import hot_controversy_chart as mod

    async def _fake_refresh(cards, **kwargs):
        await asyncio.sleep(0)
        return [{**cards[0], "controversy_meta": {"status": "ok"}}]

    monkeypatch.setattr(mod, "refresh_hot_controversy_cards", _fake_refresh)

    result = mod.refresh_hot_controversy_cards_sync([{"card_id": "card-1"}])

    assert result == [{"card_id": "card-1", "controversy_meta": {"status": "ok"}}]


@pytest.mark.asyncio
async def test_refresh_hot_controversy_cards_uses_collect_client_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import hot_controversy_chart as mod

    class FailRawRedditClient:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("hot controversy refresh must not bypass collect client fallback")

    class FakeCollectClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def fetch_post_comments(self, *args, **kwargs):
            return [
                {
                    "body": "Single provider dependency is dangerous when a platform can lock a business out with no support.",
                    "score": 11,
                    "author": "example",
                }
            ]

    created: dict[str, object] = {}

    def _fake_build_collect_reddit_client(**kwargs):
        created.update(kwargs)
        return FakeCollectClient()

    async def _fake_build_hot_controversy_result(*, card, sample, llm_client=None, llm_model=None):
        assert sample["fetch_status"] == "ok"
        assert sample["sample_size"] == 1
        return (
            {
                "support_ratio": 1.0,
                "oppose_ratio": 0.0,
                "neutral_ratio": 0.0,
                "support_point": "先做多家备份",
                "oppose_point": "封禁太黑盒",
                "neutral_point": "先看申诉入口",
                "debate_focus": "到底能不能只依赖一家",
                "dominant_side": "support",
                "confidence": "low",
            },
            {"summary_status": "ok"},
        )

    monkeypatch.setattr(mod, "RedditAPIClient", FailRawRedditClient, raising=False)
    monkeypatch.setattr(mod, "build_collect_reddit_client", _fake_build_collect_reddit_client, raising=False)
    monkeypatch.setattr(mod, "build_hot_controversy_result", _fake_build_hot_controversy_result)

    result = await mod.refresh_hot_controversy_cards(
        [
            {
                "card_id": "card-hot",
                "lane": "hot",
                "card_type": "validate",
                "source_link": "https://www.reddit.com/r/ClaudeAI/comments/1sspwz2/example",
            }
        ]
    )

    assert created["request_timeout"] == 20.0
    assert result[0]["controversy_meta"] == {"summary_status": "ok"}
    assert result[0]["controversy_chart"]["debate_focus"] == "到底能不能只依赖一家"
