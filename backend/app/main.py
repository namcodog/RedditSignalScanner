from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

try:
    # 确保在本地开发/测试时能够自动加载 backend/.env
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from app.api.v1.api import api_router as v1_api_router
from app.api.routes import (
    admin_beta_feedback_router,
    admin_facts_router,
    admin_semantic_candidates_router,
    admin_metrics_router,
    admin_tasks_router,
    admin_communities_router,
    admin_community_pool_router,
    admin_router,
    auth_router,
    beta_feedback_router,
    diagnostics_router,
    insights_router,
    metrics_router,
    guidance_router,
)
from app.core.config import Settings, get_settings
from app.db.session import DATABASE_URL, engine
from app.db.rls_sanity import should_run_rls_startup_sanity_check, verify_rls_startup_sanity
from app.middleware.route_metrics import ENABLE_ROUTE_METRICS_ENV, RouteMetricsMiddleware


async def _verify_database_identity(expected_name: str) -> None:
    """启动时校验当前连接的数据库名，防止误连旧库。"""
    async with engine.connect() as conn:
        current_db = await conn.scalar(text("SELECT current_database()"))
        if current_db != expected_name:
            raise RuntimeError(
                f"CRITICAL: Connected to wrong database: {current_db}, expected: {expected_name}"
            )


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
    app.add_middleware(RouteMetricsMiddleware)
    enable_route_metrics = os.getenv(ENABLE_ROUTE_METRICS_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if enable_route_metrics:
        from redis.asyncio import Redis

        metrics_redis_url = os.getenv("ROUTE_METRICS_REDIS_URL") or settings.reddit_cache_redis_url
        app.state.route_metrics_redis = Redis.from_url(metrics_redis_url, decode_responses=False)

    # Mount standard v1 endpoints (analyze, tasks, stream, reports, export)
    app.include_router(v1_api_router, prefix="/api")
    # 影子门牌：保持 /api 作为主入口，同时提供 /api/v1 兼容路径
    app.include_router(v1_api_router, prefix="/api/v1")

    # Mount legacy/other routers
    legacy_router = APIRouter(prefix="/api")
    legacy_router.include_router(auth_router)
    legacy_router.include_router(beta_feedback_router)
    legacy_router.include_router(admin_beta_feedback_router)
    legacy_router.include_router(admin_facts_router)
    legacy_router.include_router(admin_semantic_candidates_router)
    legacy_router.include_router(admin_metrics_router)
    legacy_router.include_router(admin_tasks_router)
    legacy_router.include_router(admin_router)
    legacy_router.include_router(admin_communities_router)
    legacy_router.include_router(admin_community_pool_router)
    legacy_router.include_router(diagnostics_router)
    legacy_router.include_router(insights_router)
    legacy_router.include_router(metrics_router)
    legacy_router.include_router(guidance_router)

    app.include_router(legacy_router)

    # 兼容旧版未版本化的健康检查
    @app.get("/api/healthz", tags=["health"])
    def health_check_alias() -> dict[str, str]:
        # 黄金路径冻结为 /api；避免返回指向不存在路径的提示文案
        return {"status": "ok"}

    @app.get("/api/v1/healthz", tags=["health"])
    def health_check_alias_v1() -> dict[str, str]:
        # 影子门牌健康检查：保持与 /api/healthz 一致
        return {"status": "ok"}

    # 根路径欢迎页面
    @app.get("/", tags=["root"])
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
                "GET  /api/v1/healthz - 健康检查 (v1 影子门牌)",
                "POST /api/auth/register - 用户注册",
                "POST /api/auth/login - 用户登录",
                "GET  /api/auth/me - 当前用户",
                "POST /api/analyze - 创建分析任务",
                "POST /api/v1/analyze - 创建分析任务 (v1 影子门牌)",
                "GET  /api/status/{task_id} - 获取任务进度",
                "GET  /api/analyze/stream/{task_id} - SSE 实时进度",
                "GET  /api/report/{task_id} - 获取分析报告",
                "POST /api/export/csv - 导出分析结果 CSV",
                "GET  /api/admin/dashboard/stats - Admin仪表盘统计",
            ],
        }

    @app.on_event("startup")
    async def verify_db_name() -> None:
        # 从连接串推导默认的数据库名，可用 EXPECTED_DATABASE_NAME 覆盖
        expected_db = os.getenv("EXPECTED_DATABASE_NAME") or make_url(
            DATABASE_URL
        ).database
        if expected_db:
            await _verify_database_identity(expected_db)

        # 合同A：启动时做一次 RLS 基础设施自检（生产/预发默认开启）
        if should_run_rls_startup_sanity_check(environment=settings.environment):
            required_user = os.getenv("RLS_REQUIRED_DB_USER", "").strip() or None
            if required_user is None and settings.environment.strip().lower() in {"production", "staging"}:
                required_user = "rss_app"

            sanity_url = os.getenv("RLS_SANITY_DATABASE_URL", "").strip() or DATABASE_URL
            await verify_rls_startup_sanity(
                database_url=sanity_url,
                required_user=required_user,
            )

    return app


settings = get_settings()
app = create_application(settings)


__all__ = ["app"]
