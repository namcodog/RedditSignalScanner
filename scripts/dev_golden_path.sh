#!/usr/bin/env bash
# Golden path launcher orchestrated outside Make recipes to ensure bash functions are available.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# shellcheck source=makefile-common.sh
. "scripts/makefile-common.sh"

echo "=========================================="
echo "🌟 Reddit Signal Scanner - 黄金启动路径"
echo "=========================================="
echo ""
echo "🧹 清理旧进程（确保环境变量生效）..."
make kill-ports 2>/dev/null || true
make kill-celery 2>/dev/null || true
echo "✅ 清理完成"
echo ""
echo "📋 启动顺序（基于 Day 12 端到端验收）："
echo "   1. Redis 服务"
echo "   2. Redis 测试数据"
echo "   3. Celery Worker"
echo "   4. 后端服务 (FastAPI)"
echo "   5. 数据库用户和任务"
echo "   6. 前端服务 (Vite)"
echo ""
echo "==> 1️⃣  启动 Redis ..."
make redis-start
redis-cli -p "${REDIS_PORT}" ping > /dev/null && echo "   ✅ Redis healthy" || echo "   ⚠️  Redis ping 失败"
echo ""
echo "==> 2️⃣  填充 Redis 测试数据 ..."
make redis-seed
echo ""
echo "==> 3️⃣  启动 Celery Worker ..."
require_backend_env
echo "   关键配置: SQLALCHEMY_DISABLE_POOL=1 (避免事件循环冲突)"
start_celery_worker background
sleep 3
tail -20 "${CELERY_WORKER_LOG}" | grep "ready" && echo "✅ Celery Worker started" || echo "⚠️  请检查日志: ${CELERY_WORKER_LOG}"
"${PYTHON_BIN}" backend/scripts/check_celery_health.py || echo "⚠️  Celery 健康检查未通过"
echo ""
echo "==> 4️⃣  数据库迁移 (Alembic upgrade) ..."
make db-upgrade || { echo "❌ 数据库迁移失败，请检查 DATABASE_URL 和 Postgres 连接"; exit 1; }
echo ""
echo "==> 5️⃣  启动后端服务 ..."
start_backend_reload
echo "   ⏳ 等待后端健康检查 ..."
for _ in {1..5}; do
  if check_backend_health; then
    echo "   ✅ Backend healthz ok"
    break
  fi
  sleep 2
done
echo ""
echo "==> 6️⃣  创建测试用户和任务 ..."
make db-seed-user-task
echo ""
echo "==> 6️⃣.1  生成洞察卡片测试数据 ..."
"${PYTHON_BIN}" backend/scripts/seed_insight_cards.py || echo "⚠️  洞察卡片种子生成失败，请检查日志"
echo ""
echo "==> 6️⃣.2  准备质量指标样例数据 ..."
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import csv
import random

metrics_dir = Path.cwd() / "reports" / "daily_metrics"
metrics_dir.mkdir(parents=True, exist_ok=True)

today = date.today()
rows = []
for offset in range(7):
    day = today - timedelta(days=offset)
    rows.append(
        {
            "date": day.isoformat(),
            "cache_hit_rate": f"{round(0.72 + random.uniform(-0.03, 0.05), 4)}",
            "valid_posts_24h": str(180 + offset * 3),
            "total_communities": str(200),
            "duplicate_rate": f"{round(0.18 + random.uniform(-0.02, 0.02), 4)}",
            "precision_at_50": f"{round(0.64 + random.uniform(-0.01, 0.02), 4)}",
            "avg_score": f"{round(0.58 + random.uniform(-0.03, 0.03), 4)}",
        }
    )

rows.sort(key=lambda x: x["date"])
by_month: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in rows:
    by_month[row["date"][:7]].append(row)

header = [
    "date",
    "cache_hit_rate",
    "valid_posts_24h",
    "total_communities",
    "duplicate_rate",
    "precision_at_50",
    "avg_score",
]

for month, data in by_month.items():
    path = metrics_dir / f"{month}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)
PY
mkdir -p backend/reports/daily_metrics
cp reports/daily_metrics/*.csv backend/reports/daily_metrics/ 2>/dev/null || true
echo "✅ 指标样例数据已准备"
echo ""
echo "==> 7️⃣  启动前端服务 ..."
start_frontend_background
echo "   ⏳ 检查前端可访问性 ..."
for _ in {1..5}; do
  if check_frontend_health; then
    echo "   ✅ Frontend ready"
    break
  fi
  sleep 2
done
echo ""
echo "=========================================="
echo "✅ 黄金路径启动完成！"
echo "=========================================="
echo ""
echo "📊 服务状态："
echo "   Redis:    ✅ redis://localhost:${REDIS_PORT}"
echo "   Celery:   ✅ tail -f ${CELERY_WORKER_LOG}"
echo "   Backend:  ✅ http://localhost:${BACKEND_PORT}"
echo "   Frontend: ✅ http://localhost:${FRONTEND_PORT}"
echo ""
echo "📝 测试数据："
echo "   用户邮箱: prd-test@example.com"
echo "   任务状态: 已完成分析"
echo ""
echo "🔗 快速访问："
echo "   前端首页:  http://localhost:${FRONTEND_PORT}/"
echo "   API 文档:  http://localhost:${BACKEND_PORT}/docs"
echo "   报告页面:  检查终端输出的任务 ID"
echo ""
echo "📋 查看日志："
echo "   Celery:   tail -f ${CELERY_WORKER_LOG}"
echo "   Backend:  tail -f /tmp/backend_uvicorn.log"
echo "   Frontend: tail -f /tmp/frontend_vite.log"
echo ""
echo "🛑 停止所有服务："
echo "   make kill-ports && make kill-celery && make kill-redis"
echo ""
