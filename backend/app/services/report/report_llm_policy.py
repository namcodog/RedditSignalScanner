from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_REASONING_MODEL = "deepseek/deepseek-v4-pro"


@dataclass(frozen=True)
class ReportLLMPolicy:
    structured_model_name: str
    narrative_model_name: str


def resolve_report_reasoning_model_name(*, fast_model_name: str) -> str:
    explicit = str(os.getenv("REPORT_REASONING_MODEL_NAME", "") or "").strip()
    if explicit:
        return explicit
    shared = str(os.getenv("HOTPOST_REASONING_MODEL", "") or "").strip()
    if shared:
        return shared
    normalized_fast = str(fast_model_name or "").strip()
    if normalized_fast == "local-extractive":
        return normalized_fast
    return _DEFAULT_REASONING_MODEL


def resolve_report_llm_policy(
    *,
    fast_model_name: str,
    reasoning_model_name: str,
    reasoning_enabled: bool,
) -> ReportLLMPolicy:
    normalized_fast = str(fast_model_name or "").strip()
    normalized_reasoning = str(reasoning_model_name or "").strip()
    reasoning_ready = (
        reasoning_enabled
        and bool(normalized_reasoning)
        and normalized_reasoning != normalized_fast
    )
    return ReportLLMPolicy(
        structured_model_name=normalized_fast,
        narrative_model_name=normalized_reasoning if reasoning_ready else normalized_fast,
    )


__all__ = [
    "ReportLLMPolicy",
    "resolve_report_llm_policy",
    "resolve_report_reasoning_model_name",
]
