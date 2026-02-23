from __future__ import annotations

from typing import Sequence
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class ExampleLibraryCreate(ORMModel):
    task_id: UUID = Field(description="源任务 ID（用于复制分析与报告）")
    title: str | None = Field(default=None, description="示例标题（可选）")
    tags: Sequence[str] | None = Field(default=None, description="示例标签（可选）")
    is_active: bool = Field(default=True, description="是否可公开展示")
