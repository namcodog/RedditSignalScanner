from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class HotpostSummaryResult:
    text: str
    source: Literal["llm", "fallback"]
    degraded_reason: str | None = None


@dataclass(frozen=True)
class HotpostLLMReportResult:
    report: dict[str, Any] | None
    source: Literal["llm", "fallback", "disabled"]
    degraded_reason: str | None = None


def normalize_hotpost_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    if value in {"queued", "waiting", "processing", "completed", "degraded", "failed"}:
        return value
    if value in {"", "success"}:
        return "completed"
    return value or "completed"


def collect_degraded_reasons(*reasons: str | None) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for reason in reasons:
        if not reason or reason in seen:
            continue
        seen.add(reason)
        output.append(reason)
    return output


def resolve_hotpost_response_status(*degraded_reasons: str | None) -> Literal["completed", "degraded"]:
    return "degraded" if any(reason for reason in degraded_reasons) else "completed"


__all__ = [
    "HotpostLLMReportResult",
    "HotpostSummaryResult",
    "collect_degraded_reasons",
    "normalize_hotpost_status",
    "resolve_hotpost_response_status",
]
