from __future__ import annotations

import json

import pytest

from app.services.hotpost.report_llm import (
    generate_hotpost_llm_report,
    render_hotpost_prompt,
)


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    async def generate(self, _prompt: str, **_kwargs: object) -> str:
        return self._content


@pytest.mark.asyncio
async def test_generate_hotpost_llm_report_parses_json() -> None:
    client = _FakeLLM('{"summary": "ok", "confidence": "high"}')
    report = await generate_hotpost_llm_report(
        mode="trending",
        query="AI tools",
        time_filter="week",
        posts_data=[{"title": "Post A", "score": 10, "comments": 5, "url": "https://reddit.com/x"}],
        comments_data=[{"body": "nice", "score": 3}],
        llm_client=client,
        max_tokens=256,
        temperature=0.1,
    )
    assert report is not None
    assert report["summary"] == "ok"


@pytest.mark.asyncio
async def test_generate_hotpost_llm_report_invalid_json_returns_none() -> None:
    client = _FakeLLM("not-json")
    report = await generate_hotpost_llm_report(
        mode="rant",
        query="Roomba",
        time_filter="all",
        posts_data=[],
        comments_data=[],
        llm_client=client,
        max_tokens=128,
        temperature=0.1,
    )
    assert report is None


def test_render_hotpost_prompt_contains_inputs() -> None:
    posts = [{"title": "Post A", "score": 10, "comments": 5, "url": "https://reddit.com/x"}]
    comments = [{"body": "nice", "score": 3}]
    prompt = render_hotpost_prompt(
        mode="trending",
        query="AI tools",
        time_filter="week",
        posts_data=posts,
        comments_data=comments,
    )
    assert "市场趋势分析师" in prompt
    assert "AI tools" in prompt
    assert json.dumps(posts, ensure_ascii=False, indent=2) in prompt
