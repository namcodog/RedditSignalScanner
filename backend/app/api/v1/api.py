from fastapi import APIRouter

from app.api.v1.endpoints import (
    analyze,
    decision_units,
    tasks,
    stream,
    reports,
    export,
    hotpost,
)

api_router = APIRouter()

api_router.include_router(analyze.router, tags=["analysis"])
api_router.include_router(decision_units.router, tags=["decision-units"])
api_router.include_router(tasks.router, tags=["tasks", "status"])
api_router.include_router(stream.router, tags=["stream"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(hotpost.router, tags=["hotpost"])
