from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field
from urllib.parse import quote_plus

try:
    # 尽早加载 backend/.env，确保所有进程（API/Celery/脚本）读取到 Reddit 凭证
    from dotenv import load_dotenv

    # 1) 仓库根目录 .env
    load_dotenv(
        dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False
    )
    # 2) backend/.env（若存在则覆盖根目录设置）
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)
except Exception:
    pass


def _default_database_url(driver: str = "postgresql+asyncpg") -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "reddit_signal_scanner")
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
    reddit_client_id: str = Field(default="")
    reddit_client_secret: str = Field(default="")
    reddit_user_agent: str = Field(default="RedditSignalScanner/1.0")
    reddit_rate_limit: int = Field(default=60)
    reddit_rate_limit_window_seconds: float = Field(default=60.0)
    reddit_request_timeout_seconds: float = Field(default=30.0)
    reddit_max_concurrency: int = Field(default=3)  # 降低并发以避免多 Worker 场景下超限
    reddit_cache_redis_url: str = Field(default_factory=_default_redis_cache_url)
    reddit_cache_ttl_seconds: int = Field(default=24 * 60 * 60)
    admin_emails_raw: str = Field(default="")
    enable_reddit_search: bool = Field(default=False)
    report_cache_ttl_seconds: int = Field(default=60 * 60)
    report_community_members_raw: str = Field(default="")
    report_target_analysis_version: str = Field(default="1.0")
    report_rate_limit_per_minute: int = Field(default=30)
    report_rate_limit_window_seconds: int = Field(default=60)
    report_export_dir: str = Field(default="reports/exports")
    default_membership_level: str = Field(default="free")

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
    )


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
