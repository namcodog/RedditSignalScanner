from __future__ import annotations

from typing import Sequence

from app.services.llm.clients.openai_client import OpenAIChatClient


class OpenAINormalizer:
    """RAG 限定的名称归一化：只在候选中挑选；无匹配返回 None。"""

    def __init__(self, model: str, *, timeout: float = 6.0) -> None:
        self._client = OpenAIChatClient(model, timeout=timeout)

    def normalize(self, name: str, *, candidates: Sequence[str]) -> str | None:
        return self._client.normalize(name, candidates=candidates)


__all__ = ["OpenAINormalizer"]

