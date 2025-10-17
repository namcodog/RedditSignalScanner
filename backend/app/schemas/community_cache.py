from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import ORMModel, TimestampedModel


class CommunityCacheRead(TimestampedModel):
    community_name: str
    last_crawled_at: datetime
    posts_cached: int = Field(ge=0)
    ttl_seconds: int = Field(gt=0)
    quality_score: Decimal = Field(ge=0, le=1)
    hit_count: int = Field(ge=0)
    crawl_priority: int = Field(ge=1, le=100)
    last_hit_at: datetime | None = None
