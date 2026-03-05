from __future__ import annotations

import os
import types
import sys

os.environ.setdefault("SKIP_DB_RESET", "1")  # 避免测试触发数据库重置

from app.services.report.t1_market_agent import ReportInputs, T1MarketReportAgent
from app.services.analysis.t1_stats import (
    T1StatsSnapshot,
    CommunityStat,
    AspectBreakdown,
    BrandPainCooccurrence,
)
from app.services.analysis.t1_clustering import PainCluster
from app.core import config


def _fake_inputs() -> ReportInputs:
    stats = T1StatsSnapshot(
        generated_at="2024-01-01T00:00:00Z",
        since_utc="2023-01-01T00:00:00Z",
        subreddits=["r/testa", "r/testb"],
        global_ps_ratio=0.6,
        community_stats=[
            CommunityStat(subreddit="testa", posts=120, comments=500, ps_ratio=0.55),
            CommunityStat(subreddit="testb", posts=80, comments=300, ps_ratio=0.4),
        ],
        aspect_breakdown=[
            AspectBreakdown(aspect="price", pain=30, total=50),
            AspectBreakdown(aspect="speed", pain=20, total=40),
        ],
        brand_pain_cooccurrence=[
            BrandPainCooccurrence(brand="BrandA", mentions=12, aspects=["price", "speed"])
        ],
    )
    clusters = [
        PainCluster(topic="费用不透明", size=25, aspects=["price"], top_keywords=["fee", "charge"], sample_comments=["a", "b"]),
        PainCluster(topic="到账慢", size=15, aspects=["speed"], top_keywords=["delay"], sample_comments=["c"]),
    ]
    return ReportInputs(stats=stats, clusters=clusters)


def test_t1_market_agent_uses_llm_when_premium(monkeypatch):
    # 强制 premium 并注入假 LLM 客户端
    monkeypatch.setattr(config.settings, "report_quality_level", "premium", raising=False)

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls = []

        def _chat_completion(self, messages, max_tokens=0, temperature=0.0):  # type: ignore[override]
            self.calls.append((messages, max_tokens, temperature))
            return "LLM_RESULT"

    stub_module = types.SimpleNamespace(OpenAIChatClient=StubClient)
    monkeypatch.setitem(sys.modules, "app.services.llm.clients.openai_client", stub_module)

    inputs = _fake_inputs()
    agent = T1MarketReportAgent(inputs)
    md = agent.render()
    assert "LLM_RESULT" in md  # 出现在至少一个增强块
    assert "LLM 增强" in md


def test_t1_market_agent_fallback_when_standard(monkeypatch):
    monkeypatch.setattr(config.settings, "report_quality_level", "standard", raising=False)
    inputs = _fake_inputs()
    agent = T1MarketReportAgent(inputs)
    md = agent.render()
    # 未启用 LLM 时仍返回模板内容
    assert "未调用 LLM" in md
    assert "商业机会（草案）" in md
