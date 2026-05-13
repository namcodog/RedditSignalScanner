from app.services.hotpost.llm_policy import resolve_hotpost_llm_policy


def test_llm_policy_routes_rant_directly_to_reasoning() -> None:
    policy = resolve_hotpost_llm_policy(
        mode="rant",
        fast_model_name="google/gemini-2.5-flash-lite",
        reasoning_model_name="openai/gpt-5.4-mini",
        reasoning_enabled=True,
    )

    assert policy.use_llm_summary is False
    assert policy.primary_report_model == "openai/gpt-5.4-mini"
    assert policy.allow_reasoning_retry is False


def test_llm_policy_keeps_trending_fast_first() -> None:
    policy = resolve_hotpost_llm_policy(
        mode="trending",
        fast_model_name="google/gemini-2.5-flash-lite",
        reasoning_model_name="openai/gpt-5.4-mini",
        reasoning_enabled=True,
    )

    assert policy.use_llm_summary is True
    assert policy.primary_report_model == "google/gemini-2.5-flash-lite"
    assert policy.allow_reasoning_retry is True
