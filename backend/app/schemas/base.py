from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )


class TimestampedModel(ORMModel):
    created_at: datetime
    updated_at: datetime
