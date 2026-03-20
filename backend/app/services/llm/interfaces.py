from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class EvidenceText:
    title: str
    note: str | None
    url: str | None


class LLMClientError(RuntimeError):
    """Raised when an LLM provider request fails at the transport layer."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        detail = f"{provider}: {message}"
        if status_code is not None:
            detail = f"{detail} (status={status_code})"
        super().__init__(detail)


class LLMClient(Protocol):
    def summarize(self, texts: Sequence[str], *, max_chars: int = 48) -> list[str]:
        ...

    def normalize(self, name: str, *, candidates: Sequence[str]) -> str | None:
        ...


class Summarizer(Protocol):
    def summarize_evidences(self, evidences: Sequence[EvidenceText], *, max_chars: int = 28) -> list[str]:
        ...


__all__ = ["EvidenceText", "LLMClient", "LLMClientError", "Summarizer"]
