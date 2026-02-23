import pytest


class _FakeLLM:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    async def generate(self, prompt, *, response_format=None, temperature=0.1, max_tokens=200):
        return self._reply


@pytest.mark.asyncio
async def test_resolve_query_no_cjk_returns_original():
    from app.services.hotpost.query_resolver import resolve_hotpost_query

    result = await resolve_hotpost_query(
        "AI tools", redis_client=None, llm_client=None
    )

    assert result.search_query == "AI tools"
    assert result.source == "original"
    assert result.keywords == []
    assert result.subreddits == []


@pytest.mark.asyncio
async def test_resolve_query_with_cjk_uses_llm():
    from app.services.hotpost.query_resolver import resolve_hotpost_query

    fake = _FakeLLM(
        '{"query_en":"robot vacuum","keywords":["Roomba","robot vacuum"],"subreddits":["RobotVacuums","r/Roomba"]}'
    )

    result = await resolve_hotpost_query(
        "扫地机器人口碑怎么样", redis_client=None, llm_client=fake
    )

    assert result.search_query == "robot vacuum"
    assert result.source == "llm"
    assert result.keywords == ["Roomba", "robot vacuum"]
    assert result.subreddits == ["r/robotvacuums", "r/roomba"]


@pytest.mark.asyncio
async def test_resolve_query_llm_bad_json_fallback():
    from app.services.hotpost.query_resolver import resolve_hotpost_query

    fake = _FakeLLM("not-json")
    result = await resolve_hotpost_query(
        "扫地机器人", redis_client=None, llm_client=fake
    )

    assert result.search_query == "扫地机器人"
    assert result.source == "fallback"
