"""Router aggregations for application endpoints."""

from __future__ import annotations

from .admin import router as admin_router
from .admin_communities import router as admin_communities_router
from .analyze import router as analyze_router
from .auth import router as auth_router
from .reports import router as report_router
from .stream import router as stream_router
from .tasks import router as task_router, status_router, tasks_router

__all__ = [
    "admin_router",
    "analyze_router",
    "auth_router",
    "admin_communities_router",
    "report_router",
    "stream_router",
    "task_router",
    "status_router",
    "tasks_router",
]
