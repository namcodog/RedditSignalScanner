from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

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


class Settings(BaseModel):
    """Application configuration derived from environment variables."""

    app_name: str = Field(default="Reddit Signal Scanner")
    environment: str = Field(default="development")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/reddit_scanner"
    )
    cors_origins_raw: str = Field(
        default="http://localhost:3006,http://127.0.0.1:3006,http://localhost:3000,http://127.0.0.1:3000"
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
    reddit_max_concurrency: int = Field(default=5)
    reddit_cache_redis_url: str = Field(default="redis://localhost:6379/5")
    reddit_cache_ttl_seconds: int = Field(default=24 * 60 * 60)
    admin_emails_raw: str = Field(default="")
    enable_reddit_search: bool = Field(default=False)

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
            "DATABASE_URL", Settings.model_fields["database_url"].default
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
            Settings.model_fields["reddit_cache_redis_url"].default,
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
    )


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
