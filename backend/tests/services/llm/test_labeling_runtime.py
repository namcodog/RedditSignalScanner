from __future__ import annotations

import json
import logging

import pytest

from app.services.llm.labeling_runtime import (
    run_label_comments_batch,
    run_label_posts_batch,
)
from app.services.llm.labeling_support import build_post_prompt, extract_batch_items


def test_build_post_prompt_truncates_body_and_top_comments() -> None:
    prompt = build_post_prompt(
        title="Payment issue",
        body="abcdefgh",
        subreddit="ecommerce",
        comments=["12345", "67890", "ignored comment"],
        max_body_chars=5,
        max_comment_chars=4,
    )

    assert prompt[0]["role"] == "system"
    user_content = prompt[1]["content"]
    assert "abcd…" in user_content
    assert "123…" in user_content
    assert "678…" in user_content
    assert "ignored comment" not in user_content


def test_extract_batch_items_filters_non_dict_values() -> None:
    parsed = {"items": [{"id": 1}, "bad", 2, {"id": 2}]}

    assert extract_batch_items(parsed) == [{"id": 1}, {"id": 2}]


@pytest.mark.asyncio
async def test_run_label_posts_batch_parses_items_payload() -> None:
    class FakeClient:
        async def generate(self, *_args, **_kwargs) -> str:
            payload = {
                "items": [
                    {
                        "id": 7,
                        "content_type": "discussion",
                        "main_intent": "ask_help",
                        "sentiment": -0.2,
                        "pain_tags": ["delay"],
                        "aspect_tags": ["support"],
                        "entities": {"known": ["paypal"], "new": []},
                        "crossborder_signals": {
                            "mentions_shipping": False,
                            "mentions_tax": True,
                        },
                        "purchase_intent_score": 0.5,
                    }
                ]
            }
            return json.dumps(payload)

    results = await run_label_posts_batch(
        client=FakeClient(),
        items=[
            {
                "id": 7,
                "title": "Need help",
                "body": "Payment delay issue",
                "subreddit": "ecommerce",
                "comments": ["any tips?"],
            }
        ],
        max_body_chars=200,
        max_comment_chars=80,
        model_name="gemini-2.5-flash-lite",
        prompt_version="v1",
        logger=logging.getLogger("test.labeling_runtime"),
    )

    assert len(results) == 1
    assert results[0]["id"] == 7
    assert results[0]["analysis"]["main_intent"] == "ask_help"
    assert results[0]["score"].business_pool in {"lab", "core", "noise"}


@pytest.mark.asyncio
async def test_run_label_comments_batch_warns_on_unparseable_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FakeClient:
        async def generate(self, *_args, **_kwargs) -> str:
            return "not-json"

    caplog.set_level(logging.WARNING)

    results = await run_label_comments_batch(
        client=FakeClient(),
        items=[
            {
                "id": 11,
                "body": "Need refund help",
                "post_title": "Refund delays",
                "subreddit": "etsy",
            }
        ],
        max_body_chars=160,
        model_name="gemini-2.5-flash-lite",
        prompt_version="v1",
        logger=logging.getLogger("test.labeling_runtime"),
    )

    assert results == []
    assert "empty_or_unparseable_response" in caplog.text
