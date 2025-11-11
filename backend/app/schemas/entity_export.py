from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EntityExportItem(BaseModel):
    name: str
    category: str
    mentions: int = Field(ge=0)


class EntityExportResponse(BaseModel):
    task_id: str
    items: list[EntityExportItem] = Field(default_factory=list)


__all__ = ["EntityExportItem", "EntityExportResponse"]

