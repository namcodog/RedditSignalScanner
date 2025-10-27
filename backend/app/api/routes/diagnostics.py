"""System diagnostics endpoints."""
from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session

router = APIRouter(prefix="/diag", tags=["diagnostics"])
logger = logging.getLogger(__name__)


@router.get("/runtime", summary="运行时诊断信息")
async def get_runtime_diagnostics(
    _payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    获取系统运行时诊断信息（需要管理员权限）。
    
    返回信息包括：
    - Python 版本和环境
    - 系统资源使用情况（CPU、内存、磁盘）
    - 数据库连接状态
    - 进程信息
    """
    # Python 环境信息
    python_info = {
        "version": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }
    
    # 系统资源信息
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
        "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage("/").percent,
    }
    
    # 进程信息
    process_info = {
        "pid": process.pid,
        "memory_rss_mb": memory_info.rss / (1024 * 1024),
        "memory_vms_mb": memory_info.vms / (1024 * 1024),
        "cpu_percent": process.cpu_percent(interval=0.1),
        "num_threads": process.num_threads(),
        "create_time": datetime.fromtimestamp(process.create_time(), tz=timezone.utc).isoformat(),
    }
    
    # 数据库连接状态
    db_status = {"connected": False, "error": None}
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status["connected"] = True
    except Exception as exc:  # pragma: no cover - logging path
        db_status["error"] = "unavailable"
        logger.warning("Database diagnostic query failed", exc_info=exc)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": python_info,
        "system": system_info,
        "process": process_info,
        "database": db_status,
    }
