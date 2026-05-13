from __future__ import annotations

from pathlib import Path

from app.services.hotpost.hotpost_config import load_hotpost_runtime_config


def test_load_hotpost_runtime_config_reads_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HOTPOST_FAST_MODEL", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_MODEL", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_ENABLED", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_TRIGGER_MODES", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_MIN_EVIDENCE", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_TRIGGER_ON_GAPS", raising=False)
    config_path = tmp_path / "hotpost_quality.yaml"
    config_path.write_text(
        """
query_resolution:
  default_time_filters:
    trending: month
    rant: all
    opportunity: month
  keyword_extraction:
    token_pattern: "[a-z]+"
    min_length: 2
    max_keywords: 4
    stopwords: ["the", "and"]
  query_planner:
    term_aliases:
      aigc: ["generative ai", "ai-generated content"]
quality_contract:
  top_quotes_limit: 2
  suggested_keywords_limit: 3
  trending_topic_limit: 2
  trend_thresholds:
    explosive_score: 400
    rising_score: 80
    rising_comments: 20
auto_remediation:
  enabled: true
  max_rounds: 1
  max_added_query_parts: 2
  max_added_subreddits: 3
  mode_terms:
    trending: ["trend"]
    rant: ["complaint"]
    opportunity: ["need"]
  gap_terms:
    missing_topics: ["latest"]
  subreddit_hints:
    trending: ["r/technology"]
    rant: ["r/rant"]
    opportunity: ["r/startups"]
llm_routing:
  fast_model: "google/gemini-2.5-flash-lite"
  reasoning_model: "openai/gpt-5.4-mini"
  reasoning_enabled: true
  reasoning_trigger_modes: ["rant", "opportunity", "trending"]
  reasoning_min_evidence: 10
  reasoning_min_evidence_by_mode:
    rant: 8
    trending: 20
  reasoning_trigger_on_gaps: true
reddit_guardrails:
  initial_query_parts_limit: 1
  initial_query_parts_limit_by_mode:
    rant: 2
  initial_subreddits_limit: 2
  initial_subreddits_limit_by_mode:
    rant: 4
  remediation_query_parts_limit: 1
  remediation_query_parts_limit_by_mode:
    rant: 2
  remediation_subreddits_limit: 2
  remediation_subreddits_limit_by_mode:
    rant: 3
  search_request_timeout_seconds: 15
  max_posts_per_subreddit: 40
  max_comment_posts: 8
  max_comment_posts_by_mode:
    rant: 12
  circuit_breaker_cooldown_seconds: 90
evidence_ranking:
  max_suggested_subreddits: 4
  opportunity_hint_priority: true
  weights:
    relevance: 5.0
    quoteability: 2.5
    freshness: 1.2
    comments: 0.8
    signals: 1.1
mode_insights:
  trending:
    explosive_hours: 48
    rising_days: 5
    sustained_days: 21
  rant:
    high_severity_percentage: 0.4
    medium_severity_percentage: 0.25
  opportunity:
    high_me_too_count: 6
    medium_me_too_count: 3
    high_wtp_bonus: 2.5
    medium_wtp_bonus: 1.2
    workaround_bonus: 1.8
evidence_packaging:
  title_max_chars: 132
  why_relevant_max_chars: 96
  focus_terms_limit: 4
  modes:
    rant:
      query_weight: 4.0
      intent_weight: 1.5
      domain_weight: 4.0
      why_relevant_weight: 1.0
      keep_focus_only: true
      min_post_score: 4.0
      min_comment_score: 3.0
    opportunity:
      query_weight: 3.0
      intent_weight: 2.0
      domain_weight: 4.0
      why_relevant_weight: 1.0
      keep_focus_only: true
      min_post_score: 6.0
      min_comment_score: 4.0
""".strip(),
        encoding="utf-8",
    )

    runtime = load_hotpost_runtime_config(config_path=config_path)

    assert runtime.query.keyword_extraction.token_pattern == "[a-z]+"
    assert runtime.query.keyword_extraction.max_keywords == 4
    assert runtime.query.default_time_filters["trending"] == "month"
    assert runtime.query.planner.term_aliases["aigc"] == [
        "generative ai",
        "ai-generated content",
    ]
    assert runtime.contract.trending_topic_limit == 2
    assert runtime.remediation.enabled is True
    assert runtime.remediation.mode_terms["trending"] == ["trend"]
    assert runtime.llm.fast_model == "google/gemini-2.5-flash-lite"
    assert runtime.llm.reasoning_model == "openai/gpt-5.4-mini"
    assert runtime.llm.reasoning_trigger_modes == ["rant", "opportunity", "trending"]
    assert runtime.llm.reasoning_min_evidence_by_mode["rant"] == 8
    assert runtime.llm.reasoning_min_evidence_by_mode["trending"] == 20
    assert runtime.reddit.max_posts_per_subreddit == 40
    assert runtime.reddit.max_comment_posts == 8
    assert runtime.reddit.initial_query_parts_limit_by_mode["rant"] == 2
    assert runtime.reddit.initial_subreddits_limit_by_mode["rant"] == 4
    assert runtime.reddit.remediation_query_parts_limit_by_mode["rant"] == 2
    assert runtime.reddit.remediation_subreddits_limit_by_mode["rant"] == 3
    assert runtime.reddit.max_comment_posts_by_mode["rant"] == 12
    assert runtime.reddit.search_request_timeout_seconds == 15.0
    assert runtime.ranking.relevance_weight == 5.0
    assert runtime.ranking.max_suggested_subreddits == 4
    assert runtime.insights.trending_explosive_hours == 48
    assert runtime.insights.rant_high_severity_percentage == 0.4
    assert runtime.insights.opportunity_high_wtp_bonus == 2.5
    assert runtime.packaging.title_max_chars == 132
    assert runtime.packaging.why_relevant_max_chars == 96
    assert runtime.packaging.focus_terms_limit == 4
    assert runtime.packaging.mode_rules["rant"].domain_weight == 4.0
    assert runtime.packaging.mode_rules["rant"].keep_focus_only is True
    assert runtime.packaging.mode_rules["opportunity"].domain_weight == 4.0
    assert runtime.packaging.mode_rules["opportunity"].keep_focus_only is True


def test_load_hotpost_runtime_config_prefers_env_for_llm_routing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "hotpost_quality.yaml"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HOTPOST_FAST_MODEL", "google/gemini-2.5-flash-lite")
    monkeypatch.setenv("HOTPOST_REASONING_MODEL", "openai/gpt-5.4-mini")
    monkeypatch.setenv("HOTPOST_REASONING_ENABLED", "false")
    monkeypatch.setenv("HOTPOST_REASONING_TRIGGER_MODES", "rant, opportunity")
    monkeypatch.setenv("HOTPOST_REASONING_MIN_EVIDENCE", "12")
    monkeypatch.setenv("HOTPOST_REASONING_TRIGGER_ON_GAPS", "false")
    monkeypatch.setenv("HOTPOST_SEARCH_REQUEST_TIMEOUT_SECONDS", "11")

    runtime = load_hotpost_runtime_config(config_path=config_path)

    assert runtime.llm.fast_model == "google/gemini-2.5-flash-lite"
    assert runtime.llm.reasoning_model == "openai/gpt-5.4-mini"
    assert runtime.llm.reasoning_enabled is False
    assert runtime.llm.reasoning_trigger_modes == ["rant", "opportunity"]
    assert runtime.llm.reasoning_min_evidence == 12
    assert runtime.llm.reasoning_min_evidence_by_mode == {}
    assert runtime.llm.reasoning_trigger_on_gaps is False
    assert runtime.reddit.search_request_timeout_seconds == 11.0
    assert runtime.reddit.initial_query_parts_limit == 1
    assert runtime.reddit.initial_query_parts_limit_by_mode == {}


def test_load_hotpost_runtime_config_defaults_fast_model_to_deepseek_flash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "hotpost_quality.yaml"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("HOTPOST_FAST_MODEL", raising=False)

    runtime = load_hotpost_runtime_config(config_path=config_path)

    assert runtime.llm.fast_model == "deepseek/deepseek-v4-flash"
