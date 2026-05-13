from __future__ import annotations

import pytest

from app.services.hotpost.hot_controversy_llm import (
    CONTROVERSY_LLM_MODEL,
    build_hot_controversy_result,
    load_hot_controversy_llm_config,
)


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict[str, object]] = []

    async def generate(self, prompt: str, **kwargs: object) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        return self._content


@pytest.mark.asyncio
async def test_build_hot_controversy_result_uses_real_counts() -> None:
    llm = _FakeLLM(
        """
        {
          "support_comments": 14,
          "oppose_comments": 8,
          "neutral_comments": 6,
          "support_point": "更像富豪安保出事，不必上升到人工智能。",
          "oppose_point": "嘴上骂人已经快变成线下威胁。",
          "neutral_point": "先看会不会再出线下跟风。",
          "debate_focus": "这到底是单次安保事件还是反人工智能情绪外溢",
          "confidence_reason": "样本里两派观点都很集中，中立评论也明确。"
        }
        """
    )
    chart, meta = await build_hot_controversy_result(
        card={
            "card_id": "card-hot",
            "title": "Sam Altman 家遭枪击",
            "summary_line": "讨论焦点已经不是案件本身。",
        },
        sample={
            "post_id": "1abc23d",
            "fetch_status": "ok",
            "sample_size": 28,
            "sampled_at": "2026-04-14T12:00:00Z",
            "sample_comments": [
                {"body": "comment a"},
                {"body": "comment b"},
            ],
        },
        llm_client=llm,
        llm_model="mimo-pretend-model",
    )

    assert chart is not None
    assert chart["support_ratio"] == 0.5
    assert chart["oppose_ratio"] == pytest.approx(0.29, abs=0.01)
    assert chart["neutral_ratio"] == pytest.approx(0.21, abs=0.01)
    assert chart["dominant_side"] == "support"
    assert chart["confidence"] == "medium"
    assert chart["debate_focus"] == "这到底是单次安保事件还是反人工智能情绪外溢"
    assert meta["post_id"] == "1abc23d"
    assert meta["sample_size"] == 28
    assert meta["fetch_status"] == "ok"
    assert meta["llm_summary_version"] == "cn_human_point_slots_v8"
    assert meta["sample_quality"] == "medium"
    assert len(llm.calls) == 1


@pytest.mark.asyncio
async def test_build_hot_controversy_result_marks_low_for_small_sample() -> None:
    llm = _FakeLLM(
        """
        {
          "support_comments": 3,
          "oppose_comments": 2,
          "neutral_comments": 1,
          "support_point": "先别慌，更像一次短期波动。",
          "oppose_point": "这不是噪音，问题已经更深了。",
          "neutral_point": "还得看下周数据稳不稳。",
          "debate_focus": "到底是短期波动还是长期恶化",
          "confidence_reason": "样本太少，只能做弱判断。"
        }
        """
    )
    chart, meta = await build_hot_controversy_result(
        card={
            "card_id": "card-hot",
            "title": "广告投放线索",
            "summary_line": "讨论开始分裂。",
        },
        sample={
            "post_id": "1small",
            "fetch_status": "ok",
            "sample_size": 6,
            "sampled_at": "2026-04-14T12:00:00Z",
            "sample_comments": [{"body": "comment a"}],
        },
        llm_client=llm,
        llm_model="gemini-2.5-flash-lite",
    )

    assert chart is not None
    assert chart["confidence"] == "low"
    assert meta["sample_quality"] == "low"
    assert meta["fetch_status"] == "ok"


@pytest.mark.asyncio
async def test_build_hot_controversy_result_does_not_fallback_to_template_ratios() -> None:
    llm = _FakeLLM("not-json")
    chart, meta = await build_hot_controversy_result(
        card={
            "card_id": "card-hot",
            "title": "Claude Mythos",
            "summary_line": "大家在吵这是技术预览还是烟雾弹。",
        },
        sample={
            "post_id": "1broken",
            "fetch_status": "ok",
            "sample_size": 24,
            "sampled_at": "2026-04-14T12:00:00Z",
            "sample_comments": [{"body": "comment a"}],
        },
        llm_client=llm,
        llm_model="gemini-2.5-flash-lite",
    )

    assert chart is None
    assert meta["fetch_status"] == "ok"
    assert meta["summary_status"] == "invalid_json"
    assert meta["sample_size"] == 24


@pytest.mark.asyncio
async def test_build_hot_controversy_result_normalizes_cn_contract_output() -> None:
    llm = _FakeLLM(
        """
        {
          "support_comments": 8,
          "oppose_comments": 7,
          "neutral_comments": 5,
          "support_point": "AI 先把量做起来，再慢慢补质量。",
          "oppose_point": "跑分好看，不等于 Claude 真能用。",
          "neutral_point": "还在观察本地机器扛不扛得住。",
          "debate_focus": "这到底是 AI 捷径还是 Claude 套壳",
          "confidence_reason": "样本分布比较平均。"
        }
        """
    )
    chart, meta = await build_hot_controversy_result(
        card={"card_id": "card-hot", "title": "Prompt 工具", "summary_line": "大家还没吵实。"},
        sample={
            "post_id": "1normalize",
            "fetch_status": "ok",
            "sample_size": 20,
            "sampled_at": "2026-04-14T12:00:00Z",
            "sample_comments": [{"body": "comment a"}],
        },
        llm_client=llm,
    )

    assert chart is not None
    assert chart["support_point"] == "人工智能先把量做起来，再慢慢补质量。"
    assert chart["oppose_point"] == "跑分好看，不等于模型真能用。"
    assert chart["neutral_point"] == "先看本地机器扛不扛得住。"
    assert chart["debate_focus"] == "这到底是人工智能捷径还是模型套壳"
    assert meta["summary_status"] == "ok"


@pytest.mark.asyncio
async def test_build_hot_controversy_result_locks_model_to_gemini25lite(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _FakeLLM(
        """
        {
          "support_comments": 4,
          "oppose_comments": 3,
          "neutral_comments": 3,
          "support_point": "先把量做起来，再慢慢补质量。",
          "oppose_point": "跑分好看，不等于真能用。",
          "neutral_point": "先看后面转化能不能跟上。",
          "debate_focus": "这到底是拿量捷径还是垃圾内容",
          "confidence_reason": "样本里有分歧。"
        }
        """
    )
    captured: dict[str, object] = {}

    def _fake_builder(model_name: str, *, timeout: float) -> _FakeLLM:
        captured["model_name"] = model_name
        captured["timeout"] = timeout
        return llm

    monkeypatch.setattr("app.services.hotpost.hot_controversy_llm.build_card_content_client", _fake_builder)
    chart, meta = await build_hot_controversy_result(
        card={"card_id": "card-hot", "title": "Claude Mythos", "summary_line": "大家在吵。"},
        sample={
            "post_id": "1lock",
            "fetch_status": "ok",
            "sample_size": 18,
            "sampled_at": "2026-04-14T12:00:00Z",
            "sample_comments": [{"body": "comment a"}],
        },
        llm_model="openai/gpt-4.1",
    )

    assert chart is not None
    assert meta["summary_status"] == "ok"
    assert captured["model_name"] == CONTROVERSY_LLM_MODEL


def test_load_hot_controversy_llm_config_reads_governed_model() -> None:
    load_hot_controversy_llm_config.cache_clear()
    try:
        config = load_hot_controversy_llm_config()
    finally:
        load_hot_controversy_llm_config.cache_clear()

    assert config["model"] == "google/gemini-2.5-flash-lite"
    assert config["summary_version"] == "cn_human_point_slots_v8"
    assert config["timeout_seconds"] == 20.0
