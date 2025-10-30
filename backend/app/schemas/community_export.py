from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CommunityExportItem(BaseModel):
    name: str
    mentions: int = Field(ge=0)
    relevance: Optional[int] = Field(default=None, ge=0, le=100)
    category: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    daily_posts: Optional[int] = Field(default=None, ge=0)
    avg_comment_length: Optional[int] = Field(default=None, ge=0)
    from_cache: Optional[bool] = None
    cache_hit_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    members: Optional[int] = Field(default=None, ge=0)

    # 治理/抓取扩展
    priority: Optional[str] = None
    tier: Optional[str] = None
    is_blacklisted: Optional[bool] = None
    blacklist_reason: Optional[str] = None
    is_active: Optional[bool] = None
    crawl_frequency_hours: Optional[int] = Field(default=None, ge=0)
    crawl_priority: Optional[int] = Field(default=None, ge=1, le=100)
    last_crawled_at: Optional[datetime] = None
    posts_cached: Optional[int] = Field(default=None, ge=0)
    hit_count: Optional[int] = Field(default=None, ge=0)
    empty_hit: Optional[int] = Field(default=None, ge=0)
    failure_hit: Optional[int] = Field(default=None, ge=0)
    success_hit: Optional[int] = Field(default=None, ge=0)


class CommunityExportResponse(BaseModel):
    task_id: str
    scope: str = Field(description="导出范围：top 或 all")
    seed_source: Optional[str] = None
    top_n: Optional[int] = None
    total_communities: Optional[int] = None
    items: list[CommunityExportItem] = Field(default_factory=list)


__all__ = ["CommunityExportItem", "CommunityExportResponse"]

