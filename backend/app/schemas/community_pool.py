"""Pydantic schemas for community pool and discovered communities."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import ORMModel


class PendingCommunityCreate(ORMModel):
    """Schema for creating a new pending community (discovered from analysis)."""

    name: str = Field(min_length=3, max_length=100, description="Community name (e.g., 'artificial')")
    discovered_from_keywords: dict[str, Any] | None = Field(
        default=None, description="Keywords that led to discovery"
    )
    discovered_from_task_id: UUID | None = Field(default=None, description="Task ID that discovered this community")

    @field_validator("name")  # type: ignore[misc]
    @classmethod
    def validate_community_name(cls, v: str) -> str:
        """Validate community name format."""
        v = v.strip().lower()
        if v.startswith("r/"):
            v = v[2:]
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Community name must be alphanumeric (with _ or - allowed)")
        return v


class PendingCommunityUpdate(ORMModel):
    """Schema for updating a pending community (admin review)."""

    status: str = Field(description="Status: pending/approved/rejected")
    admin_notes: str | None = Field(default=None, max_length=1000, description="Admin review notes")
    reviewed_by: UUID | None = Field(default=None, description="Admin user ID who reviewed")

    @field_validator("status")  # type: ignore[misc]
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        allowed = {"pending", "approved", "rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v


class PendingCommunityResponse(ORMModel):
    """Schema for pending community response."""

    id: int
    name: str
    discovered_from_keywords: dict[str, Any] | None
    discovered_count: int
    first_discovered_at: datetime
    last_discovered_at: datetime
    status: str
    admin_reviewed_at: datetime | None
    admin_notes: str | None
    discovered_from_task_id: UUID | None
    reviewed_by: UUID | None


class CommunityPoolStats(ORMModel):
    """Schema for community pool statistics."""

    total_communities: int = Field(description="Total communities in pool")
    active_communities: int = Field(description="Active communities")
    inactive_communities: int = Field(description="Inactive communities")
    pending_discoveries: int = Field(description="Pending community discoveries")
    approved_discoveries: int = Field(description="Approved discoveries")
    rejected_discoveries: int = Field(description="Rejected discoveries")
    avg_quality_score: float = Field(description="Average quality score")
    cache_coverage: float = Field(ge=0.0, le=1.0, description="Cache coverage ratio (0-1)")


class CommunityPoolItem(ORMModel):
    """Schema for a single community pool item."""

    id: int
    name: str
    tier: str
    categories: dict[str, Any]
    description_keywords: dict[str, Any]
    daily_posts: int
    avg_comment_length: int
    quality_score: float
    priority: str
    user_feedback_count: int
    discovered_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CommunityPoolListResponse(ORMModel):
    """Schema for community pool list response."""

    communities: list[CommunityPoolItem]
    total: int
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")


class CommunityCacheUpdate(ORMModel):
    """Schema for updating community cache metadata."""

    crawl_frequency_hours: int | None = Field(default=None, ge=1, le=168, description="Crawl frequency in hours")
    is_active: bool | None = Field(default=None, description="Whether community is active")
    crawl_priority: int | None = Field(default=None, ge=1, le=100, description="Crawl priority (1-100)")


class WarmupMetrics(ORMModel):
    """Schema for warmup period metrics."""

    period_start: datetime
    period_end: datetime
    total_communities_cached: int
    total_posts_cached: int
    cache_hit_rate: float = Field(ge=0.0, le=1.0, description="Cache hit rate (0-1)")
    avg_cache_age_hours: float
    total_api_calls: int
    avg_api_calls_per_minute: float
    peak_api_calls_per_minute: int
    total_analyses: int
    avg_analysis_time_seconds: float
    p95_analysis_time_seconds: float
    system_uptime_percentage: float = Field(ge=0.0, le=100.0, description="System uptime %")


class CommunityDiscoveryRequest(ORMModel):
    """Schema for requesting community discovery from product description."""

    product_description: str = Field(min_length=10, max_length=5000, description="Product description")
    task_id: UUID = Field(description="Task ID for tracking")
    max_communities: int = Field(default=10, ge=1, le=50, description="Max communities to discover")


class CommunityDiscoveryResponse(ORMModel):
    """Schema for community discovery response."""

    discovered_communities: list[str]
    keywords_used: list[str]
    total_discovered: int
    already_in_pool: list[str]
    newly_discovered: list[str]

