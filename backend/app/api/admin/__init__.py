from __future__ import annotations

from fastapi import APIRouter

from app.api.admin import semantic_candidates
from app.api.admin import metrics
from app.api.admin import tasks

api_router = APIRouter()
api_router.include_router(semantic_candidates.router)
api_router.include_router(metrics.router)
api_router.include_router(tasks.router)

__all__ = ["api_router"]
