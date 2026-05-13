from fastapi import APIRouter

from app.api.v1.endpoints import (
    analyze,
    brand_intelligence,
    decision_units,
    tasks,
    stream,
    reports,
    export,
    hotpost,
    hotpost_clues,
    hotpost_card_candidates,
    hotpost_card_drafts,
    hotpost_card_review,
    hotpost_wx_auth,
    hotpost_wx_favorites,
    hotpost_source_scopes,
    hotpost_candidate_collection,
)

api_router = APIRouter()

api_router.include_router(analyze.router, tags=["analysis"])
api_router.include_router(brand_intelligence.router)
api_router.include_router(decision_units.router, tags=["decision-units"])
api_router.include_router(tasks.router, tags=["tasks", "status"])
api_router.include_router(stream.router, tags=["stream"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(hotpost.router, tags=["hotpost"])

api_router.include_router(hotpost_clues.router)
api_router.include_router(hotpost_card_candidates.router)
api_router.include_router(hotpost_card_drafts.router)
api_router.include_router(hotpost_card_review.router)
api_router.include_router(hotpost_wx_auth.router)
api_router.include_router(hotpost_wx_favorites.router)
api_router.include_router(hotpost_source_scopes.router)
api_router.include_router(hotpost_candidate_collection.router)
