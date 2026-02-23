from __future__ import annotations

"""
MarketingCopyGenerator: 生成四类中文营销短文案（<=40字）。

variants:
- vs_subscription: 反订阅类（"为什么每年多花..."）
- vs_competitor: 对比竞品（替代/更省心）
- pain_resonance: 痛点共鸣（"我们受够了..."）
- value_prop: 价值主张（产品+关键价值）

支持两种模式：
- 模板模式（默认）：纯本地、安全可测
- LLM 模式（可选）：按 TitleSlogan 模式组装 prompts，失败自动降级
"""

from dataclasses import dataclass
from typing import Mapping

from app.services.llm.clients.openai_client import OpenAIChatClient


MAX_LEN = 40


@dataclass(slots=True)
class CopyAmmo:
    vs_subscription: str
    vs_competitor: str
    pain_resonance: str
    value_prop: str

    def to_dict(self) -> dict[str, str]:
        return {
            "vs_subscription": self.vs_subscription,
            "vs_competitor": self.vs_competitor,
            "pain_resonance": self.pain_resonance,
            "value_prop": self.value_prop,
        }


class MarketingCopyGenerator:
    def __init__(self, model: str = "gpt-4o-mini", *, llm_enabled: bool = False, timeout: float = 8.0) -> None:
        self._model = model
        self._llm_enabled = llm_enabled
        self._timeout = timeout
        self._client: OpenAIChatClient | None = None
        if llm_enabled:
            try:
                self._client = OpenAIChatClient(model, timeout=timeout)
            except Exception:
                # 无可用凭据/SDK时自动降级
                self._client = None

    def generate(self, context: Mapping[str, object]) -> CopyAmmo:
        if self._llm_enabled and self._client is not None:
            out = self._gen_llm(context)
            if out is not None:
                return out
        return self._gen_template(context)

    # ---------------- template mode ----------------

    def _gen_template(self, context: Mapping[str, object]) -> CopyAmmo:
        product = _str(context.get("product"), default="这款产品")
        competitor = _str(context.get("competitor"), default="竞品")
        pain = _str(context.get("pain"), default="反复手工、效率低")
        value = _str(context.get("value"), default="自动化提效，一键上线")
        sub = _str(context.get("subscription"), default="每年订阅费")

        vs_sub = _limit(f"为什么每年多花{_normalize_price(sub)}？{product}一次搞定")
        vs_comp = _limit(f"{product}替代{competitor}，更轻更省心")
        pain_res = _limit(f"我们受够了{pain}，{product}说再见")
        value_prop = _limit(f"{product}：{value}")
        return CopyAmmo(
            vs_subscription=vs_sub,
            vs_competitor=vs_comp,
            pain_resonance=pain_res,
            value_prop=value_prop,
        )

    # ---------------- llm mode ----------------

    def _gen_llm(self, context: Mapping[str, object]) -> CopyAmmo | None:
        client = self._client
        if client is None:
            return None
        product = _str(context.get("product"), default="这款产品")
        competitor = _str(context.get("competitor"), default="竞品")
        pain = _str(context.get("pain"), default="反复手工、效率低")
        value = _str(context.get("value"), default="自动化提效，一键上线")
        sub = _str(context.get("subscription"), default="每年订阅费")

        try:
            vs_sub = client._chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是营销文案助手。只依据提供信息，不得编造；必须中文，<=40字，"
                            "语气坚定但不过度夸张，避免万能词。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"产品名: {product}\n订阅: {sub}\n\n"
                            "写一句'对订阅说不'风格文案，<=40字，只输出结果："
                        ),
                    },
                ],
                max_tokens=64,
                temperature=0.3,
            )
            vs_comp = client._chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是营销文案助手。必须中文，<=40字；强调替代竞品、轻量省心，不夸大。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"产品名: {product}\n竞品: {competitor}\n\n"
                            "写一句对比竞品的替代文案，<=40字，只输出结果："
                        ),
                    },
                ],
                max_tokens=64,
                temperature=0.3,
            )
            pain_res = client._chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是营销文案助手。必须中文，<=40字；以'我们受够了…'共鸣痛点开头。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"产品名: {product}\n痛点: {pain}\n\n"
                            "写一句共鸣痛点的短文案，<=40字，只输出结果："
                        ),
                    },
                ],
                max_tokens=64,
                temperature=0.25,
            )
            value_prop = client._chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是营销文案助手。必须中文，<=40字；精炼表达产品价值，不要形容词堆砌。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"产品名: {product}\n价值: {value}\n\n"
                            "写一句价值主张短句，<=40字，只输出结果："
                        ),
                    },
                ],
                max_tokens=64,
                temperature=0.25,
            )

            return CopyAmmo(
                vs_subscription=_limit(vs_sub),
                vs_competitor=_limit(vs_comp),
                pain_resonance=_limit(pain_res),
                value_prop=_limit(value_prop),
            )
        except Exception:
            return None


# ---------------- small helpers ----------------

def _limit(text: str) -> str:
    t = (text or "").strip().splitlines()[0].strip()
    if len(t) > MAX_LEN:
        return t[: MAX_LEN - 1] + "…"
    return t


def _normalize_price(text: str) -> str:
    # 简化处理：输入中若带数字则保留原样，否则返回“订阅费”
    t = (text or "").strip()
    return t if any(ch.isdigit() for ch in t) else "订阅费"


def _str(value: object | None, *, default: str) -> str:
    s = str(value or "").strip()
    return s if s else default


__all__ = ["MarketingCopyGenerator", "CopyAmmo", "MAX_LEN"]

