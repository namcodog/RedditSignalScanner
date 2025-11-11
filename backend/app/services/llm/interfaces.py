from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class EvidenceText:
    title: str
    note: str | None
    url: str | None


class LLMClient(Protocol):
    def summarize(self, texts: Sequence[str], *, max_chars: int = 48) -> list[str]:
        ...

    def normalize(self, name: str, *, candidates: Sequence[str]) -> str | None:
        ...


class Summarizer(Protocol):
    def summarize_evidences(self, evidences: Sequence[EvidenceText], *, max_chars: int = 28) -> list[str]:
        ...


__all__ = ["EvidenceText", "LLMClient", "Summarizer"]

