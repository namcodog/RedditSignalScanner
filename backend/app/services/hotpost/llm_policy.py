from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HotpostLLMPolicy:
    use_llm_summary: bool
    primary_report_model: str
    allow_reasoning_retry: bool


def resolve_hotpost_llm_policy(
    *,
    mode: str,
    fast_model_name: str,
    reasoning_model_name: str,
    reasoning_enabled: bool,
) -> HotpostLLMPolicy:
    normalized_mode = str(mode or "").strip().lower()
    reasoning_ready = (
        reasoning_enabled
        and bool(reasoning_model_name)
        and reasoning_model_name != fast_model_name
    )

    if normalized_mode == "rant":
        return HotpostLLMPolicy(
            use_llm_summary=False,
            primary_report_model=reasoning_model_name if reasoning_ready else fast_model_name,
            allow_reasoning_retry=False,
        )

    return HotpostLLMPolicy(
        use_llm_summary=True,
        primary_report_model=fast_model_name,
        allow_reasoning_retry=reasoning_ready,
    )


__all__ = ["HotpostLLMPolicy", "resolve_hotpost_llm_policy"]
