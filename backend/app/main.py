from __future__ import annotations

from fastapi import FastAPI
from pathlib import Path
try:
    # 确保在本地开发/测试时能够自动加载 backend/.env
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from app.api.routes import (
    admin_router,
    admin_communities_router,
    admin_community_pool_router,
    analyze_router,
    auth_router,
    report_router,
    status_router,
    stream_router,
    task_router,
    tasks_router,
    beta_feedback_router,
    admin_beta_feedback_router,
)
from app.core.config import Settings, get_settings


def create_application(settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Reddit Signal Scanner API (Phase 1/2 implementation)",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api")
    api_router.include_router(auth_router)
    api_router.include_router(analyze_router)
    api_router.include_router(status_router)
    api_router.include_router(stream_router)
    api_router.include_router(task_router)
    api_router.include_router(report_router)
    api_router.include_router(tasks_router)
    api_router.include_router(beta_feedback_router)
    api_router.include_router(admin_beta_feedback_router)
    api_router.include_router(admin_router)
    api_router.include_router(admin_communities_router)
    api_router.include_router(admin_community_pool_router)

    @api_router.get("/healthz", tags=["health"])  # type: ignore[misc]
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @api_router.get("/diag/runtime", tags=["health"])  # type: ignore[misc]
    def runtime_diag() -> dict[str, str | bool]:
        cfg = get_settings()
        return {
            "has_reddit_client": bool(cfg.reddit_client_id and cfg.reddit_client_secret),
            "app_env": cfg.environment,
            "sse_base_path": cfg.sse_base_path,
        }

    app.include_router(api_router)

    # 根路径欢迎页面
    @app.get("/", tags=["root"])  # type: ignore[misc]
    def root() -> dict[str, str | list[str]]:
        """
        API 根路径 - 返回服务信息和可用端点
        """
        return {
            "service": settings.app_name,
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "endpoints": [
                "GET  /api/healthz - 健康检查",
                "POST /api/auth/register - 用户注册",
                "POST /api/auth/login - 用户登录",
                "POST /api/analyze - 创建分析任务",
                "GET  /api/status/{task_id} - 获取任务进度",
                "GET  /api/stream/{task_id} - SSE 实时进度",
                "GET  /api/tasks/{task_id} - 获取任务状态",
                "GET  /api/reports/{task_id} - 获取分析报告",
                "GET  /api/admin/dashboard/stats - Admin仪表盘统计",
            ],
        }

    return app


settings = get_settings()
app = create_application(settings)


__all__ = ["app"]
