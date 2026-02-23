from __future__ import annotations

import json

import pytest

from app.services.llm.labeling import LLMLabeler


@pytest.mark.asyncio
async def test_llm_labeler_parses_post_json() -> None:
    labeler = LLMLabeler(
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        max_body_chars=200,
        max_comment_chars=80,
        api_key="test",
    )

    async def fake_generate(*_args, **_kwargs) -> str:
        payload = {
            "content_type": "user_review",
            "main_intent": "complain",
            "sentiment": -0.4,
            "pain_tags": ["fee", "delay"],
            "aspect_tags": ["pricing"],
            "entities": {"known": ["paypal"], "new": []},
            "crossborder_signals": {"mentions_shipping": False, "mentions_tax": True},
            "purchase_intent_score": 0.9,
        }
        return json.dumps(payload)

    labeler._client.generate = fake_generate  # type: ignore[attr-defined]

    analysis, score, in_chars, out_chars = await labeler.label_post(
        title="Payment fee issue",
        body="Fees are too high and settlement is slow.",
        subreddit="ecommerce",
        comments=["This fee is painful."],
    )

    assert analysis["main_intent"] == "complain"
    assert analysis["purchase_intent_score"] == 0.9
    assert score.business_pool == "core"
    assert in_chars > 0
    assert out_chars > 0


@pytest.mark.asyncio
async def test_llm_labeler_parses_comment_json() -> None:
    labeler = LLMLabeler(
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        max_body_chars=160,
        max_comment_chars=60,
        api_key="test",
    )

    async def fake_generate(*_args, **_kwargs) -> str:
        payload = {
            "actor_type": "buyer_ask",
            "main_intent": "ask_help",
            "sentiment": 0.1,
            "pain_tags": ["refund"],
            "aspect_tags": ["support"],
            "entities": {"known": [], "new": ["etsy"]},
            "crossborder_signals": {"mentions_shipping": True, "mentions_tax": False},
            "purchase_intent_score": 0.4,
        }
        return json.dumps(payload)

    labeler._client.generate = fake_generate  # type: ignore[attr-defined]

    analysis, score, in_chars, out_chars = await labeler.label_comment(
        body="Need help with refunds.",
        post_title="Refund delays",
        subreddit="etsy",
    )

    assert analysis["actor_type"] == "buyer_ask"
    assert analysis["pain_tags"] == ["refund"]
    assert score.business_pool in {"lab", "core", "noise"}
    assert in_chars > 0
    assert out_chars > 0


@pytest.mark.asyncio
async def test_llm_labeler_batch_parses_posts() -> None:
    labeler = LLMLabeler(
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        max_body_chars=200,
        max_comment_chars=80,
        api_key="test",
    )

    async def fake_generate(*_args, **_kwargs) -> str:
        payload = [
            {
                "id": 1,
                "content_type": "discussion",
                "main_intent": "ask_help",
                "sentiment": -0.2,
                "pain_tags": ["delay"],
                "aspect_tags": ["support"],
                "entities": {"known": ["paypal"], "new": []},
                "crossborder_signals": {"mentions_shipping": False, "mentions_tax": True},
                "purchase_intent_score": 0.5,
            },
            {
                "id": 2,
                "content_type": "user_review",
                "main_intent": "recommend_product",
                "sentiment": 0.6,
                "pain_tags": [],
                "aspect_tags": ["pricing"],
                "entities": {"known": ["stripe"], "new": []},
                "crossborder_signals": {"mentions_shipping": True, "mentions_tax": False},
                "purchase_intent_score": 0.7,
            },
        ]
        return json.dumps(payload)

    labeler._client.generate = fake_generate  # type: ignore[attr-defined]

    results = await labeler.label_posts_batch(
        items=[
            {
                "id": 1,
                "title": "Need help",
                "body": "Payment delay issue",
                "subreddit": "ecommerce",
                "comments": ["any tips?"],
            },
            {
                "id": 2,
                "title": "Great pricing",
                "body": "Loved the fee transparency",
                "subreddit": "payments",
                "comments": [],
            },
        ]
    )

    assert {r["id"] for r in results} == {1, 2}
    assert any(r["score"].business_pool in {"lab", "core", "noise"} for r in results)


@pytest.mark.asyncio
async def test_llm_labeler_batch_parses_comments() -> None:
    labeler = LLMLabeler(
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        max_body_chars=160,
        max_comment_chars=60,
        api_key="test",
    )

    async def fake_generate(*_args, **_kwargs) -> str:
        payload = [
            {
                "id": 11,
                "actor_type": "buyer_ask",
                "main_intent": "ask_help",
                "sentiment": -0.1,
                "pain_tags": ["refund"],
                "aspect_tags": ["support"],
                "entities": {"known": [], "new": ["etsy"]},
                "crossborder_signals": {"mentions_shipping": False, "mentions_tax": False},
                "purchase_intent_score": 0.2,
            }
        ]
        return json.dumps(payload)

    labeler._client.generate = fake_generate  # type: ignore[attr-defined]

    results = await labeler.label_comments_batch(
        items=[
            {
                "id": 11,
                "body": "Need refund help",
                "post_title": "Refund delays",
                "subreddit": "etsy",
            }
        ]
    )

    assert results[0]["id"] == 11
    assert results[0]["analysis"]["actor_type"] == "buyer_ask"
