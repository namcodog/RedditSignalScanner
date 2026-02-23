from __future__ import annotations

import types

from app.services.llm.marketing_copy import MarketingCopyGenerator, MAX_LEN


def test_template_generation_variants_and_limits() -> None:
    ctx = {
        "product": "快书CRM",
        "competitor": "竞品X",
        "pain": "反复手动导入客户、流程混乱",
        "value": "自动化跟进+一键建档",
        "subscription": "每年¥1999",
    }
    gen = MarketingCopyGenerator(llm_enabled=False)
    out = gen.generate(ctx).to_dict()
    assert set(out.keys()) == {"vs_subscription", "vs_competitor", "pain_resonance", "value_prop"}
    for v in out.values():
        assert isinstance(v, str)
        assert 0 < len(v) <= MAX_LEN
        # 不应残留模板槽位
        assert "{" not in v and "}" not in v


def test_llm_mode_uses_client_when_available(monkeypatch) -> None:
    # 构造一个最小可用的 stub，避免真实网络依赖和凭据
    class _DummyClient:
        def __init__(self, model: str, *, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def _chat_completion(self, messages, *, max_tokens: int, temperature: float) -> str:  # noqa: ARG002
            # 根据提示大概返回一段短句
            content = messages[-1]["content"] if messages else ""
            if "订阅" in content:
                return "别再为订阅多花钱，快书CRM一次到位"
            if "竞品" in content:
                return "快书CRM替代竞品X，更省心"
            if "痛点" in content:
                return "我们受够了反复手工，快书CRM说再见"
            return "快书CRM：自动化提效，一键上线"

    # 将模块里的 OpenAIChatClient 指向 stub
    import app.services.llm.marketing_copy as mc

    monkeypatch.setattr(mc, "OpenAIChatClient", _DummyClient, raising=True)

    ctx = {
        "product": "快书CRM",
        "competitor": "竞品X",
        "pain": "反复手动导入客户、流程混乱",
        "value": "自动化跟进+一键建档",
        "subscription": "每年¥1999",
    }
    gen = mc.MarketingCopyGenerator(llm_enabled=True)
    out = gen.generate(ctx).to_dict()
    # 验证 LLM 分支走通且限长
    for v in out.values():
        assert 0 < len(v) <= MAX_LEN


def test_llm_fallback_to_template_when_error(monkeypatch) -> None:
    # 制造一个会抛异常的 client，使其走降级
    class _BadClient:
        def __init__(self, model: str, *, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def _chat_completion(self, *args, **kwargs):  # noqa: ANN001, ANN002
            raise RuntimeError("boom")

    import app.services.llm.marketing_copy as mc

    monkeypatch.setattr(mc, "OpenAIChatClient", _BadClient, raising=True)

    ctx = {"product": "快书CRM"}
    gen = mc.MarketingCopyGenerator(llm_enabled=True)
    out = gen.generate(ctx).to_dict()
    # 降级后依然应当有 4 个非空文案
    for v in out.values():
        assert isinstance(v, str) and len(v) > 0


def test_template_handles_missing_partial_data() -> None:
    # 缺少 competitor/subscription/value 时，模板应使用兜底词而不是留下占位符
    ctx = {
        "product": "简记AI",
        # competitor/subscription/value 均缺失
        "pain": "反复复制粘贴、资料分散",
    }
    gen = MarketingCopyGenerator(llm_enabled=False)
    out = gen.generate(ctx).to_dict()
    assert set(out.keys()) == {"vs_subscription", "vs_competitor", "pain_resonance", "value_prop"}
    for k, v in out.items():
        assert isinstance(v, str) and len(v) > 0
        assert "{" not in v and "}" not in v
