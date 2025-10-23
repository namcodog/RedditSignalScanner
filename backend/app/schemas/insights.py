from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class EvidenceResponse(ORMModel):
    """证据响应 Schema"""

    id: UUID = Field(description="证据 ID")
    post_url: str = Field(description="原帖 URL", max_length=500)
    excerpt: str = Field(description="摘录内容")
    timestamp: datetime = Field(description="帖子时间戳")
    subreddit: str = Field(description="子版块名称", max_length=100)
    score: float = Field(description="证据分数 (0.0-1.0)", ge=0.0, le=1.0)


class InsightCardResponse(ORMModel):
    """洞察卡片响应 Schema"""

    id: UUID = Field(description="洞察卡片 ID")
    task_id: UUID = Field(description="关联的分析任务 ID")
    title: str = Field(description="洞察卡片标题", max_length=500)
    summary: str = Field(description="洞察摘要")
    confidence: float = Field(description="置信度分数 (0.0-1.0)", ge=0.0, le=1.0)
    time_window_days: int = Field(description="时间窗口（天数）", gt=0)
    subreddits: list[str] = Field(description="相关子版块列表", default_factory=list)
    evidences: list[EvidenceResponse] = Field(
        description="证据列表", default_factory=list
    )
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class InsightCardListResponse(ORMModel):
    """洞察卡片列表响应 Schema"""

    total: int = Field(description="总数", ge=0)
    items: list[InsightCardResponse] = Field(
        description="洞察卡片列表", default_factory=list
    )


__all__ = [
    "EvidenceResponse",
    "InsightCardResponse",
    "InsightCardListResponse",
]

