from __future__ import annotations

from typing import List, Sequence

from app.services.llm.interfaces import EvidenceText, Summarizer
from app.services.llm.clients.openai_client import OpenAIChatClient


class OpenAISummarizer(Summarizer):
    def __init__(self, *, model: str, timeout: float = 8.0) -> None:
        self._client = OpenAIChatClient(model, timeout=timeout)

    def summarize_evidences(self, evidences: Sequence[EvidenceText], *, max_chars: int = 28) -> list[str]:
        texts: List[str] = []
        for ev in evidences:
            base = (ev.title or "").strip()
            if not base:
                base = (ev.note or "").strip()
            texts.append(base)
        return self._client.summarize(texts, max_chars=max_chars)


__all__ = ["OpenAISummarizer"]

