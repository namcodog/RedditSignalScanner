from __future__ import annotations

from typing import Sequence

from app.services.llm.clients.openai_client import OpenAIChatClient


class TitleSloganGenerator:
    def __init__(self, model: str, *, timeout: float = 8.0) -> None:
        self._client = OpenAIChatClient(model, timeout=timeout)

    def generate_title(self, description: str, *, max_chars: int = 16) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是产品报告的标题助手。只能在用户提供的描述中抽取或极短改写，不得编造。"
                    f"只输出一个标题，<= {max_chars} 字，中文，避免夸张形容词。"
                ),
            },
            {
                "role": "user",
                "content": f"机会描述：{(description or '').strip()}\n输出：",
            },
        ]
        out = self._client._chat_completion(messages, max_tokens=max(48, max_chars * 3), temperature=0.2)
        out = (out or "").splitlines()[0].strip()
        if len(out) > max_chars:
            out = out[: max_chars - 1] + "…"
        return out

    def generate_slogan(self, description: str, *, max_chars: int = 20) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是产品口号助手。基于描述抽取一句简洁口号，不得编造，避免绝对化、避免英语，"
                    f"只输出一句中文，<= {max_chars} 字。"
                ),
            },
            {
                "role": "user",
                "content": f"机会描述：{(description or '').strip()}\n输出：",
            },
        ]
        out = self._client._chat_completion(messages, max_tokens=max(60, max_chars * 3), temperature=0.25)
        out = (out or "").splitlines()[0].strip()
        if len(out) > max_chars:
            out = out[: max_chars - 1] + "…"
        return out


__all__ = ["TitleSloganGenerator"]

