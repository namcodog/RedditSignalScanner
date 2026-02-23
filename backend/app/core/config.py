from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field
from urllib.parse import quote_plus

def _load_dotenv_with_precedence(
    *,
    root_env: Path,
    backend_env: Path,
    root_env_local: Path | None = None,
    backend_env_local: Path | None = None,
) -> None:
    """
    加载 .env 的“优先级规则”（大白话）：

    1) 你在 shell/CI 里显式设置的变量最优先，.env 不能盖掉它（避免“我明明 export 了还不生效”）。
    2) backend/.env 可以覆盖根目录 .env 的占位值（避免根目录 .env 里写了空值/旧值）。
    """

    try:
        from dotenv import dotenv_values
    except Exception:
        return

    preexisting_keys = set(os.environ.keys())

    def _apply(values: dict[str, str | None], *, override_existing: bool) -> None:
        for key, value in values.items():
            if value is None:
                continue
            # 不覆盖“进程启动时就存在”的 shell/CI 值
            if key in preexisting_keys:
                continue
            if not override_existing and key in os.environ:
                continue
            os.environ[key] = str(value)

    try:
        root_values = dotenv_values(dotenv_path=root_env)
    except Exception:
        root_values = {}
    _apply(root_values, override_existing=False)

    try:
        backend_values = dotenv_values(dotenv_path=backend_env)
    except Exception:
        backend_values = {}
    _apply(backend_values, override_existing=True)

    if root_env_local is not None:
        try:
            root_local_values = dotenv_values(dotenv_path=root_env_local)
        except Exception:
            root_local_values = {}
        _apply(root_local_values, override_existing=True)

    if backend_env_local is not None:
        try:
            backend_local_values = dotenv_values(dotenv_path=backend_env_local)
        except Exception:
            backend_local_values = {}
        _apply(backend_local_values, override_existing=True)


try:
    # 尽早加载 .env，避免“本地跑起来一堆变量缺失”。
    # 注意：这里遵循上面的优先级规则，避免 backend/.env 把 shell 显式配置盖掉。
    root_env_path = Path(__file__).resolve().parents[3] / ".env"
    backend_env_path = Path(__file__).resolve().parents[2] / ".env"
    root_env_local_path = Path(__file__).resolve().parents[3] / ".env.local"
    backend_env_local_path = Path(__file__).resolve().parents[2] / ".env.local"
    _load_dotenv_with_precedence(
        root_env=root_env_path,
        backend_env=backend_env_path,
        root_env_local=root_env_local_path,
        backend_env_local=backend_env_local_path,
    )
except Exception:
    pass


def _default_database_url(driver: str = "postgresql+asyncpg") -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "reddit_signal_scanner_dev")
    return f"{driver}://{user}:{password}@{host}:{port}/{name}"


def _default_redis_cache_url(db_index: str | None = None) -> str:
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = db_index or os.getenv("REDIS_CACHE_DB", "5")
    return f"redis://{host}:{port}/{db}"


DEFAULT_COMMUNITY_MEMBERS: Dict[str, int] = {
    "r/startups": 1_200_000,
    "r/entrepreneur": 980_000,
    "r/saas": 450_000,
    "r/productmanagement": 320_000,
    "r/technology": 1_000_000,
    "r/artificial": 500_000,
    "r/userexperience": 260_000,
    "r/growthhacking": 180_000,
    "r/smallbusiness": 210_000,
    "r/marketing": 750_000,
}


class Settings(BaseModel):
    """Application configuration derived from environment variables."""

    app_name: str = Field(default="Reddit Signal Scanner")
    environment: str = Field(default="development")
    database_url: str = Field(default_factory=lambda: _default_database_url("postgresql+psycopg"))
    cors_origins_raw: str = Field(
        default="http://localhost:3006,http://127.0.0.1:3006,http://localhost:3007,http://127.0.0.1:3007,http://localhost:3008,http://127.0.0.1:3008,http://localhost:3009,http://127.0.0.1:3009,http://localhost:3000,http://127.0.0.1:3000"
    )
    jwt_secret: str = Field(default="insecure-development-secret")
    jwt_algorithm: str = Field(default="HS256")
    sse_base_path: str = Field(default="/api/analyze/stream")
    estimated_processing_minutes: int = Field(default=5)
    allow_mock_fallback: bool = Field(default=False)
    enable_mock_data: bool = Field(default=False)
    reddit_client_id: str = Field(default="")
    reddit_client_secret: str = Field(default="")
    reddit_user_agent: str = Field(default="RedditSignalScanner/1.0")
    # Reddit API 限流配置（对齐官方建议：60 req/min，使用 10 分钟窗口更稳定）
    reddit_rate_limit: int = Field(default=58)  # 留 2 个请求余量
    reddit_rate_limit_window_seconds: float = Field(default=60.0)  # 60 秒窗口
    reddit_request_timeout_seconds: float = Field(default=30.0)
    reddit_max_concurrency: int = Field(default=2)  # 降低并发避免突发流量  # 降低并发以避免多 Worker 场景下超限
    reddit_cache_redis_url: str = Field(default_factory=_default_redis_cache_url)
    reddit_cache_ttl_seconds: int = Field(default=24 * 60 * 60)
    # Deprecated: only kept for backward compatibility; preview uses incremental_comments_preview_enabled.
    enable_comments_sync: bool = Field(default=True)
    incremental_comments_preview_enabled: bool = Field(default=True)
    comments_topn_limit: int = Field(default=20)
    incremental_spam_filter_mode: str = Field(default="tag")
    incremental_duplicate_mode: str = Field(default="tag")
    incremental_comments_backfill_enabled: bool = Field(default=True)
    incremental_comments_backfill_mode: str = Field(default="smart_shallow")
    incremental_comments_backfill_max_posts: int = Field(default=5)
    incremental_comments_backfill_limit: int = Field(default=50)
    incremental_comments_backfill_depth: int = Field(default=2)
    # 补跑补偿（延迟分批 + 抖动）
    compensation_delay_enabled: bool = Field(default=True)
    compensation_base_delay_seconds: int = Field(default=30)
    compensation_max_delay_seconds: int = Field(default=900)
    compensation_jitter_seconds: int = Field(default=10)
    compensation_batch_size: int = Field(default=25)
    admin_emails_raw: str = Field(default="")
    enable_reddit_search: bool = Field(default=False)
    enable_hybrid_retrieval: bool = Field(default=True)
    hybrid_post_limit: int = Field(default=200)
    hybrid_vector_distance: float = Field(default=0.4)
    hybrid_weight: float = Field(default=0.7)
    enable_vector_dedup: bool = Field(default=True)
    vector_dedup_threshold: float = Field(default=0.92)
    report_cache_ttl_seconds: int = Field(default=60 * 60)
    report_community_members_raw: str = Field(default="")
    report_target_analysis_version: str = Field(default="1.0")
    report_rate_limit_per_minute: int = Field(default=30)
    report_rate_limit_window_seconds: int = Field(default=60)
    report_export_dir: str = Field(default="reports/exports")
    default_membership_level: str = Field(default="free")
    # LLM 增益（必开：可回退）
    enable_llm_summary: bool = Field(default=True)
    llm_model_name: str = Field(default="local-extractive")
    gemini_api_key: str = Field(default="")
    llm_label_model_name: str = Field(default="gemini-2.5-flash-lite")
    # 报告阶段的同步 LLM 增益（默认关闭，避免 /api/report 阻塞）
    enable_report_inline_llm: bool = Field(default=False)
    # LLM 打标签/打分（离线增强）
    llm_label_lookback_days: int = Field(default=90)
    llm_label_post_limit: int = Field(default=500)
    llm_label_comment_limit: int = Field(default=500)
    llm_label_body_chars: int = Field(default=800)
    llm_label_comment_chars: int = Field(default=400)
    llm_label_prompt_version: str = Field(default="v1")
    # LLM 候选回流语义库
    llm_semantic_lookback_days: int = Field(default=90)
    llm_semantic_post_limit: int = Field(default=5000)
    llm_semantic_comment_limit: int = Field(default=5000)
    llm_semantic_min_confidence: float = Field(default=0.85)
    llm_semantic_min_frequency: int = Field(default=5)
    llm_semantic_min_communities: int = Field(default=2)
    llm_semantic_min_authors: int = Field(default=3)
    llm_semantic_auto_approve: bool = Field(default=True)
    # Market report (optional, non-breaking)
    enable_market_report: bool = Field(default=False)
    # Unified Lexicon rollout (semantic unification)
    enable_unified_lexicon: bool = Field(default=False)
    semantic_lexicon_path: str = Field(default="backend/config/semantic_sets/unified_lexicon.yml")
    market_report_template_path: str = Field(default="backend/config/report_templates/market_insight_v1.md")
    # Comments retention (days) for TTL cleanup
    comments_retention_days: int = Field(default=180)
    # 报告模式（可选）：executive / market
    report_mode: str = Field(default="executive")
    # 报告质量等级：basic | standard | premium
    report_quality_level: str = Field(default="standard")
    openai_api_key: str = Field(default="")

    @property
    def cors_origins(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def admin_emails(self) -> List[str]:
        return [
            email.strip().lower()
            for email in self.admin_emails_raw.split(",")
            if email.strip()
        ]

    @property
    def report_community_members(self) -> Dict[str, int]:
        if not self.report_community_members_raw:
            return DEFAULT_COMMUNITY_MEMBERS.copy()
        try:
            payload = json.loads(self.report_community_members_raw)
        except json.JSONDecodeError:
            return DEFAULT_COMMUNITY_MEMBERS.copy()

        result: Dict[str, int] = DEFAULT_COMMUNITY_MEMBERS.copy()
        for name, value in payload.items():
            try:
                result[str(name).lower()] = int(value)
            except (TypeError, ValueError):
                continue
        return result

    @property
    def REDDIT_CLIENT_ID(self) -> str:
        """Reddit API client ID."""
        return self.reddit_client_id

    @property
    def REDDIT_CLIENT_SECRET(self) -> str:
        """Reddit API client secret."""
        return self.reddit_client_secret

    @property
    def REDDIT_USER_AGENT(self) -> str:
        """Reddit API user agent."""
        return self.reddit_user_agent

    @property
    def OPENAI_API_KEY(self) -> str:
        """OpenAI API key."""
        return self.openai_api_key


@lru_cache()
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", _default_database_url("postgresql+psycopg")
        ),
        cors_origins_raw=os.getenv(
            "CORS_ALLOW_ORIGINS", Settings.model_fields["cors_origins_raw"].default
        ),
        jwt_secret=os.getenv("JWT_SECRET", Settings.model_fields["jwt_secret"].default),
        jwt_algorithm=os.getenv(
            "JWT_ALGORITHM", Settings.model_fields["jwt_algorithm"].default
        ),
        allow_mock_fallback=str(os.getenv("ALLOW_MOCK_FALLBACK", "0"))
        .strip()
        .lower()
        in {"1", "true", "yes"},
        environment=os.getenv("APP_ENV", Settings.model_fields["environment"].default),
        reddit_client_id=os.getenv(
            "REDDIT_CLIENT_ID", Settings.model_fields["reddit_client_id"].default
        ),
        reddit_client_secret=os.getenv(
            "REDDIT_CLIENT_SECRET",
            Settings.model_fields["reddit_client_secret"].default,
        ),
        reddit_user_agent=os.getenv(
            "REDDIT_USER_AGENT", Settings.model_fields["reddit_user_agent"].default
        ),
        reddit_rate_limit=int(
            os.getenv(
                "REDDIT_RATE_LIMIT", Settings.model_fields["reddit_rate_limit"].default
            )
        ),
        reddit_rate_limit_window_seconds=float(
            os.getenv(
                "REDDIT_RATE_LIMIT_WINDOW_SECONDS",
                Settings.model_fields["reddit_rate_limit_window_seconds"].default,
            )
        ),
        reddit_request_timeout_seconds=float(
            os.getenv(
                "REDDIT_REQUEST_TIMEOUT_SECONDS",
                Settings.model_fields["reddit_request_timeout_seconds"].default,
            )
        ),
        reddit_max_concurrency=int(
            os.getenv(
                "REDDIT_MAX_CONCURRENCY",
                Settings.model_fields["reddit_max_concurrency"].default,
            )
        ),
        reddit_cache_redis_url=os.getenv(
            "REDDIT_CACHE_REDIS_URL",
            _default_redis_cache_url(),
        ),
        reddit_cache_ttl_seconds=int(
            os.getenv(
                "REDDIT_CACHE_TTL_SECONDS",
                Settings.model_fields["reddit_cache_ttl_seconds"].default,
            )
        ),
        enable_comments_sync=os.getenv("ENABLE_COMMENTS_SYNC", "true").strip().lower()
        in {"1", "true", "yes"},
        incremental_comments_preview_enabled=(
            os.getenv("INCREMENTAL_COMMENTS_PREVIEW_ENABLED")
            if os.getenv("INCREMENTAL_COMMENTS_PREVIEW_ENABLED") is not None
            else os.getenv("ENABLE_COMMENTS_SYNC", "true")
        )
        .strip()
        .lower()
        in {"1", "true", "yes"},
        comments_topn_limit=int(
            os.getenv(
                "COMMENTS_TOPN_LIMIT",
                Settings.model_fields["comments_topn_limit"].default,
            )
        ),
        incremental_spam_filter_mode=os.getenv(
            "INCREMENTAL_SPAM_FILTER_MODE",
            Settings.model_fields["incremental_spam_filter_mode"].default,
        ),
        incremental_duplicate_mode=os.getenv(
            "INCREMENTAL_DUPLICATE_MODE",
            Settings.model_fields["incremental_duplicate_mode"].default,
        ),
        incremental_comments_backfill_enabled=os.getenv(
            "INCREMENTAL_COMMENTS_BACKFILL_ENABLED",
            str(Settings.model_fields["incremental_comments_backfill_enabled"].default).lower(),
        )
        .strip()
        .lower()
        in {"1", "true", "yes"},
        incremental_comments_backfill_mode=os.getenv(
            "INCREMENTAL_COMMENTS_BACKFILL_MODE",
            Settings.model_fields["incremental_comments_backfill_mode"].default,
        ),
        incremental_comments_backfill_max_posts=int(
            os.getenv(
                "INCREMENTAL_COMMENTS_BACKFILL_MAX_POSTS",
                Settings.model_fields["incremental_comments_backfill_max_posts"].default,
            )
        ),
        incremental_comments_backfill_limit=int(
            os.getenv(
                "INCREMENTAL_COMMENTS_BACKFILL_LIMIT",
                Settings.model_fields["incremental_comments_backfill_limit"].default,
            )
        ),
        incremental_comments_backfill_depth=int(
            os.getenv(
                "INCREMENTAL_COMMENTS_BACKFILL_DEPTH",
                Settings.model_fields["incremental_comments_backfill_depth"].default,
            )
        ),
        compensation_delay_enabled=os.getenv(
            "COMPENSATION_DELAY_ENABLED",
            str(Settings.model_fields["compensation_delay_enabled"].default).lower(),
        )
        .strip()
        .lower()
        in {"1", "true", "yes"},
        compensation_base_delay_seconds=int(
            os.getenv(
                "COMPENSATION_BASE_DELAY_SECONDS",
                Settings.model_fields["compensation_base_delay_seconds"].default,
            )
        ),
        compensation_max_delay_seconds=int(
            os.getenv(
                "COMPENSATION_MAX_DELAY_SECONDS",
                Settings.model_fields["compensation_max_delay_seconds"].default,
            )
        ),
        compensation_jitter_seconds=int(
            os.getenv(
                "COMPENSATION_JITTER_SECONDS",
                Settings.model_fields["compensation_jitter_seconds"].default,
            )
        ),
        compensation_batch_size=int(
            os.getenv(
                "COMPENSATION_BATCH_SIZE",
                Settings.model_fields["compensation_batch_size"].default,
            )
        ),
        admin_emails_raw=os.getenv(
            "ADMIN_EMAILS",
            Settings.model_fields["admin_emails_raw"].default,
        ),
        enable_reddit_search=os.getenv("ENABLE_REDDIT_SEARCH", "false")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        report_cache_ttl_seconds=int(
            os.getenv(
                "REPORT_CACHE_TTL_SECONDS",
                Settings.model_fields["report_cache_ttl_seconds"].default,
            )
        ),
        report_rate_limit_per_minute=int(
            os.getenv(
                "REPORT_RATE_LIMIT_PER_MINUTE",
                Settings.model_fields["report_rate_limit_per_minute"].default,
            )
        ),
        report_rate_limit_window_seconds=int(
            os.getenv(
                "REPORT_RATE_LIMIT_WINDOW_SECONDS",
                Settings.model_fields["report_rate_limit_window_seconds"].default,
            )
        ),
        report_export_dir=os.getenv(
            "REPORT_EXPORT_DIR",
            Settings.model_fields["report_export_dir"].default,
        ),
        report_community_members_raw=os.getenv(
            "REPORT_COMMUNITY_MEMBERS",
            Settings.model_fields["report_community_members_raw"].default,
        ),
        report_target_analysis_version=os.getenv(
            "REPORT_TARGET_ANALYSIS_VERSION",
            Settings.model_fields["report_target_analysis_version"].default,
        ),
        default_membership_level=os.getenv(
            "DEFAULT_MEMBERSHIP_LEVEL",
            Settings.model_fields["default_membership_level"].default,
        ),
        enable_llm_summary=os.getenv("ENABLE_LLM_SUMMARY", "true").strip().lower()
        in {"1", "true", "yes"},
        llm_model_name=os.getenv("LLM_MODEL_NAME", "x-ai/grok-4.1-fast"),
        gemini_api_key=os.getenv(
            "GEMINI_API_KEY",
            Settings.model_fields["gemini_api_key"].default,
        ),
        llm_label_model_name=os.getenv(
            "LLM_LABEL_MODEL_NAME",
            Settings.model_fields["llm_label_model_name"].default,
        ),
        enable_report_inline_llm=os.getenv("ENABLE_REPORT_INLINE_LLM", "false")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        llm_label_lookback_days=int(
            os.getenv(
                "LLM_LABEL_LOOKBACK_DAYS",
                Settings.model_fields["llm_label_lookback_days"].default,
            )
        ),
        llm_label_post_limit=int(
            os.getenv(
                "LLM_LABEL_POST_LIMIT",
                Settings.model_fields["llm_label_post_limit"].default,
            )
        ),
        llm_label_comment_limit=int(
            os.getenv(
                "LLM_LABEL_COMMENT_LIMIT",
                Settings.model_fields["llm_label_comment_limit"].default,
            )
        ),
        llm_label_body_chars=int(
            os.getenv(
                "LLM_LABEL_BODY_CHARS",
                Settings.model_fields["llm_label_body_chars"].default,
            )
        ),
        llm_label_comment_chars=int(
            os.getenv(
                "LLM_LABEL_COMMENT_CHARS",
                Settings.model_fields["llm_label_comment_chars"].default,
            )
        ),
        llm_label_prompt_version=os.getenv(
            "LLM_LABEL_PROMPT_VERSION",
            Settings.model_fields["llm_label_prompt_version"].default,
        ),
        llm_semantic_lookback_days=int(
            os.getenv(
                "LLM_SEMANTIC_LOOKBACK_DAYS",
                Settings.model_fields["llm_semantic_lookback_days"].default,
            )
        ),
        llm_semantic_post_limit=int(
            os.getenv(
                "LLM_SEMANTIC_POST_LIMIT",
                Settings.model_fields["llm_semantic_post_limit"].default,
            )
        ),
        llm_semantic_comment_limit=int(
            os.getenv(
                "LLM_SEMANTIC_COMMENT_LIMIT",
                Settings.model_fields["llm_semantic_comment_limit"].default,
            )
        ),
        llm_semantic_min_confidence=float(
            os.getenv(
                "LLM_SEMANTIC_MIN_CONFIDENCE",
                Settings.model_fields["llm_semantic_min_confidence"].default,
            )
        ),
        llm_semantic_min_frequency=int(
            os.getenv(
                "LLM_SEMANTIC_MIN_FREQUENCY",
                Settings.model_fields["llm_semantic_min_frequency"].default,
            )
        ),
        llm_semantic_min_communities=int(
            os.getenv(
                "LLM_SEMANTIC_MIN_COMMUNITIES",
                Settings.model_fields["llm_semantic_min_communities"].default,
            )
        ),
        llm_semantic_min_authors=int(
            os.getenv(
                "LLM_SEMANTIC_MIN_AUTHORS",
                Settings.model_fields["llm_semantic_min_authors"].default,
            )
        ),
        llm_semantic_auto_approve=os.getenv(
            "LLM_SEMANTIC_AUTO_APPROVE", "true"
        )
        .strip()
        .lower()
        in {"1", "true", "yes"},
        enable_market_report=os.getenv("ENABLE_MARKET_REPORT", "false")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        enable_unified_lexicon=os.getenv("ENABLE_UNIFIED_LEXICON", "false")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        semantic_lexicon_path=os.getenv(
            "SEMANTIC_LEXICON_PATH",
            Settings.model_fields["semantic_lexicon_path"].default,
        ),
        market_report_template_path=os.getenv(
            "MARKET_REPORT_TEMPLATE",
            Settings.model_fields["market_report_template_path"].default,
        ),
        comments_retention_days=int(
            os.getenv(
                "COMMENTS_RETENTION_DAYS",
                Settings.model_fields["comments_retention_days"].default,
            )
        ),
        report_mode=os.getenv(
            "REPORT_MODE", Settings.model_fields["report_mode"].default
        ).strip().lower(),
        report_quality_level=os.getenv(
            "REPORT_QUALITY_LEVEL",
            Settings.model_fields["report_quality_level"].default,
        ).strip().lower(),
        openai_api_key=(
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or Settings.model_fields["openai_api_key"].default
        ),
    )


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
