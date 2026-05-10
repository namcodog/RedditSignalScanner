from app.services.report.report_llm_policy import (
    resolve_report_llm_policy,
    resolve_report_reasoning_model_name,
)


def test_report_policy_keeps_structured_fast_and_narrative_reasoning() -> None:
    policy = resolve_report_llm_policy(
        fast_model_name="x-ai/grok-4.1-fast",
        reasoning_model_name="openai/gpt-5.4-mini",
        reasoning_enabled=True,
    )

    assert policy.structured_model_name == "x-ai/grok-4.1-fast"
    assert policy.narrative_model_name == "openai/gpt-5.4-mini"


def test_report_policy_falls_back_to_fast_when_reasoning_disabled() -> None:
    policy = resolve_report_llm_policy(
        fast_model_name="x-ai/grok-4.1-fast",
        reasoning_model_name="openai/gpt-5.4-mini",
        reasoning_enabled=False,
    )

    assert policy.structured_model_name == "x-ai/grok-4.1-fast"
    assert policy.narrative_model_name == "x-ai/grok-4.1-fast"


def test_report_reasoning_model_prefers_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("REPORT_REASONING_MODEL_NAME", "openai/gpt-5.4-mini")
    monkeypatch.setenv("HOTPOST_REASONING_MODEL", "deepseek/deepseek-v4-pro")

    model_name = resolve_report_reasoning_model_name(
        fast_model_name="x-ai/grok-4.1-fast",
    )

    assert model_name == "openai/gpt-5.4-mini"
