from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """洞察证据条目

    注意：不使用 from_attributes=True，因为我们在 Service 层手动构造
    """

    id: UUID = Field(description="证据 ID")
    post_id: str | None = Field(
        default=None,
        description="原帖 ID（可选，可用于回查 Reddit 帖子）",
        max_length=32,
    )
    post_url: str = Field(description="原帖 URL", max_length=500)
    excerpt: str = Field(description="证据摘录内容")
    timestamp: datetime = Field(description="帖子时间戳")
    subreddit: str = Field(description="子版块名称", max_length=100)
    score: float | None = Field(
        default=None,
        description="证据分数 (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class InsightCardResponse(BaseModel):
    """洞察卡片响应 Schema

    注意：不使用 from_attributes=True，因为我们在 Service 层手动构造
    避免 Pydantic 递归访问 ORM 关系导致 RecursionError
    """

    id: UUID = Field(description="洞察卡片 ID")
    task_id: UUID = Field(description="关联的分析任务 ID")
    title: str = Field(description="洞察卡片标题", max_length=500)
    summary: str = Field(description="洞察摘要")
    confidence: float = Field(description="置信度分数 (0.0-1.0)", ge=0.0, le=1.0)
    time_window: str = Field(description="时间窗口说明，例如“过去 30 天”")
    time_window_days: int = Field(description="时间窗口（天数）", gt=0)
    subreddits: list[str] = Field(
        description="相关子版块列表",
        default_factory=list,
    )
    evidence: list[EvidenceItem] = Field(
        description="证据列表",
        default_factory=list,
    )
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class InsightCardListResponse(BaseModel):
    """洞察卡片列表响应 Schema"""

    total: int = Field(description="总数", ge=0)
    items: list[InsightCardResponse] = Field(
        description="洞察卡片列表",
        default_factory=list,
    )


__all__ = [
    "EvidenceItem",
    "InsightCardResponse",
    "InsightCardListResponse",
]
