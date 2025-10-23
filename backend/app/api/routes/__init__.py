"""Router aggregations for application endpoints."""

from __future__ import annotations

from .admin import router as admin_router
from .admin_beta_feedback import router as admin_beta_feedback_router
from .admin_communities import router as admin_communities_router
from .admin_community_pool import router as admin_community_pool_router
from .analyze import router as analyze_router
from .auth import router as auth_router
from .beta_feedback import router as beta_feedback_router
from .diagnostics import router as diagnostics_router
from .insights import router as insights_router
from .metrics import router as metrics_router
from .reports import router as report_router
from .stream import router as stream_router
from .tasks import router as task_router
from .tasks import status_router, tasks_router

__all__ = [
    "admin_router",
    "analyze_router",
    "auth_router",
    "admin_communities_router",
    "admin_community_pool_router",
    "beta_feedback_router",
    "admin_beta_feedback_router",
    "diagnostics_router",
    "insights_router",
    "metrics_router",
    "report_router",
    "stream_router",
    "task_router",
    "status_router",
    "tasks_router",
]
