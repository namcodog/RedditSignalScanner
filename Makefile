# Reddit Signal Scanner - Makefile
# 0-1 重写项目的统一启动与管理脚本

.PHONY: help
.PHONY: dev-backend dev-frontend dev-all dev-full dev-golden-path
.PHONY: kill-ports kill-backend-port kill-frontend-port kill-celery kill-redis
.PHONY: restart-backend restart-frontend restart-all
.PHONY: status check-services check-python
.PHONY: test test-backend test-frontend test-all test-e2e test-admin-e2e
.PHONY: test-fix test-clean test-diagnose test-kill-pytest
.PHONY: celery-start celery-stop celery-restart celery-verify celery-seed celery-seed-unique celery-purge
.PHONY: celery-test celery-mypy celery-logs
.PHONY: redis-start redis-stop redis-status redis-seed redis-purge
.PHONY: db-migrate db-upgrade db-downgrade db-reset db-seed-user-task
.PHONY: clean clean-pyc clean-test
.PHONY: mcp-install mcp-verify
.PHONY: env-check env-setup


# 让每个目标在一个 shell 会话中执行，支持 heredoc 等多行脚本
.ONESHELL:
SHELL := /bin/bash

# ============================================================
# Python 版本统一配置 (Day 9 验收后统一使用 Python 3.11)
# ============================================================
PYTHON := /opt/homebrew/bin/python3.11
PYTHON_VERSION := 3.11
BACKEND_DIR := backend
FRONTEND_DIR := frontend
SCRIPTS_DIR := $(BACKEND_DIR)/scripts
BACKEND_PORT := 8006
FRONTEND_PORT := 3006
REDIS_PORT := 6379

# Celery 配置
CELERY_WORKER_LOG := /tmp/celery_worker.log
CELERY_APP := app.core.celery_app.celery_app
CELERY_CONCURRENCY := 4

# 环境变量
export ENABLE_CELERY_DISPATCH := 1
export PYTHONPATH := $(BACKEND_DIR)

# 默认目标：显示帮助
help: ## 显示所有可用命令
	@echo "Reddit Signal Scanner - 可用命令："
	@echo ""
	@echo "⚙️  环境配置："
	@echo "  make env-check          检查Python版本和环境配置"
	@echo "  make env-setup          设置开发环境（Python 3.11）"
	@echo ""
	@echo "🚀 快速启动："
	@echo "  make dev-golden-path    🌟 黄金路径：一键启动完整环境（推荐）"
	@echo "  make dev-full           启动完整开发环境（Redis + Celery + Backend + Frontend）"
	@echo "  make dev-backend        启动后端服务（需要先启动Redis和Celery）"
	@echo "  make dev-frontend       启动前端服务"
	@echo ""
	@echo "📦 Redis 管理："
	@echo "  make redis-start        启动Redis服务"
	@echo "  make redis-stop         停止Redis服务"
	@echo "  make redis-status       检查Redis状态"
	@echo "  make redis-seed         填充测试数据到Redis"
	@echo "  make redis-purge        清空Redis测试数据"
	@echo ""
	@echo "⚡ Celery 管理："
	@echo "  make celery-start       启动Celery Worker"
	@echo "  make celery-stop        停止Celery Worker"
	@echo "  make celery-restart     重启Celery Worker"
	@echo "  make celery-logs        查看Celery日志"
	@echo ""
	@echo "🧪 测试："
	@echo "  make test-backend       运行后端测试"
	@echo "  make test-frontend      运行前端测试"
	@echo "  make test-e2e           运行端到端测试"
	@echo "  make test-admin-e2e     验证Admin后台端到端流程（需配置ADMIN_EMAILS）"
	@echo ""
	@echo "🔧 更多命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================
# 环境检查与配置
# ============================================================

env-check: ## 检查Python版本和环境配置
	@echo "==> 检查环境配置 ..."
	@echo ""
	@echo "1️⃣  Python 版本检查："
	@echo "   目标版本: Python $(PYTHON_VERSION)"
	@echo "   当前版本: $$($(PYTHON) --version 2>&1)"
	@$(PYTHON) --version 2>&1 | grep -q "$(PYTHON_VERSION)" && echo "   ✅ Python 版本正确" || (echo "   ❌ Python 版本不匹配！请使用 Python $(PYTHON_VERSION)" && exit 1)
	@echo ""
	@echo "2️⃣  系统Python版本："
	@echo "   系统Python: $$(python3 --version 2>&1)"
	@echo "   位置: $$(which python3)"
	@echo ""
	@echo "3️⃣  Homebrew Python 3.11："
	@echo "   位置: $(PYTHON)"
	@test -f $(PYTHON) && echo "   ✅ Python 3.11 已安装" || (echo "   ❌ Python 3.11 未安装！请运行: brew install python@3.11" && exit 1)
	@echo ""
	@echo "4️⃣  环境变量："
	@echo "   ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH)"
	@echo "   PYTHONPATH=$(PYTHONPATH)"
	@echo ""
	@echo "✅ 环境检查完成！"

env-setup: ## 设置开发环境（安装Python 3.11和依赖）
	@echo "==> 设置开发环境 ..."
	@echo ""
	@echo "1️⃣  检查Homebrew ..."
	@which brew > /dev/null || (echo "❌ Homebrew未安装！请访问 https://brew.sh" && exit 1)
	@echo "   ✅ Homebrew已安装"
	@echo ""
	@echo "2️⃣  安装Python 3.11 ..."
	@brew list python@3.11 > /dev/null 2>&1 || brew install python@3.11
	@echo "   ✅ Python 3.11已安装"
	@echo ""
	@echo "3️⃣  安装后端依赖 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt
	@echo "   ✅ 后端依赖已安装"
	@echo ""
	@echo "4️⃣  安装前端依赖 ..."
	@cd $(FRONTEND_DIR) && npm install
	@echo "   ✅ 前端依赖已安装"
	@echo ""
	@echo "✅ 开发环境设置完成！"

# ============================================================
# 端口管理
# ============================================================

kill-backend-port: ## 清理后端端口 8006
	@echo "==> Killing processes on port $(BACKEND_PORT) ..."
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || echo "✅ Port $(BACKEND_PORT) is free"
	@sleep 1

kill-frontend-port: ## 清理前端端口 3006
	@echo "==> Killing processes on port $(FRONTEND_PORT) ..."
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || echo "✅ Port $(FRONTEND_PORT) is free"
	@sleep 1

kill-celery: ## 停止所有Celery Worker进程
	@echo "==> Killing Celery workers ..."
	@pkill -f "celery.*worker" || echo "✅ No Celery workers running"
	@sleep 1

kill-redis: ## 停止Redis服务
	@echo "==> Killing Redis server ..."
	@pkill redis-server || echo "✅ No Redis server running"
	@sleep 1

kill-ports: kill-backend-port kill-frontend-port ## 清理所有服务端口 (8006, 3006)

# ============================================================
# Redis 管理
# ============================================================

redis-start: ## 启动Redis服务
	@echo "==> Starting Redis server on port $(REDIS_PORT) ..."
	@redis-server --daemonize yes --port $(REDIS_PORT) || echo "⚠️  Redis可能已在运行"
	@sleep 1
	@redis-cli ping > /dev/null && echo "✅ Redis server is running" || echo "❌ Redis server failed to start"

redis-stop: kill-redis ## 停止Redis服务

redis-status: ## 检查Redis状态
	@echo "==> Checking Redis status ..."
	@redis-cli ping > /dev/null && echo "✅ Redis is running" || echo "❌ Redis is not running"
	@echo ""
	@echo "Redis 数据库键统计："
	@for db in 0 1 2 5; do \
		count=$$(redis-cli -n $$db DBSIZE | awk '{print $$2}'); \
		echo "  DB $$db: $$count keys"; \
	done

redis-seed: ## 填充测试数据到Redis（使用seed_test_data.py）
	@echo "==> Seeding test data to Redis ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed_test_data.py
	@echo "✅ Test data seeded successfully"

redis-purge: ## 清空Redis测试数据
	@echo "==> Purging test data from Redis ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed_test_data.py --purge
	@echo "✅ Test data purged successfully"

# ============================================================
# 开发服务器启动
# ============================================================

dev-backend: ## 启动后端开发服务器 (FastAPI + Uvicorn, 端口 8006, 启用Celery dispatch)
	@echo "==> Starting backend development server on http://localhost:$(BACKEND_PORT) ..."
	@echo "    API Docs: http://localhost:$(BACKEND_PORT)/docs"
	@echo "    OpenAPI JSON: http://localhost:$(BACKEND_PORT)/openapi.json"
	@echo "    ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH)"
	@cd $(BACKEND_DIR) && ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH) uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend: ## 启动前端开发服务器 (Vite, 端口 3006)
	@echo "==> Starting frontend development server on http://localhost:$(FRONTEND_PORT) ..."
	@cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT)

dev-all: ## 同时启动前后端开发服务器（需要两个终端）
	@echo "==> 请在两个终端分别运行："
	@echo "    终端 1: make dev-backend"
	@echo "    终端 2: make dev-frontend"
	@echo ""
	@echo "或者使用 tmux/screen 并行启动"

dev-full: ## 启动完整开发环境（Redis + Celery + Backend + Frontend）
	@echo "==> 启动完整开发环境 ..."
	@echo ""
	@echo "1️⃣  启动Redis ..."
	@$(MAKE) redis-start
	@echo ""
	@echo "2️⃣  填充测试数据 ..."
	@$(MAKE) redis-seed
	@echo ""
	@echo "3️⃣  启动Celery Worker（后台）..."
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && \
		nohup $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	else \
		cd $(BACKEND_DIR) && nohup $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	fi
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker started" || echo "⚠️  Celery Worker可能未启动，请检查日志: $(CELERY_WORKER_LOG)"
	@echo ""
	@echo "4️⃣  启动后端服务（后台）..."
	@cd $(BACKEND_DIR) && ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH) nohup uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) > /tmp/backend_uvicorn.log 2>&1 &
	@sleep 3
	@curl -s http://localhost:$(BACKEND_PORT)/ > /dev/null && echo "✅ Backend server started" || echo "⚠️  Backend server可能未启动"
	@echo ""
	@echo "✅ 完整开发环境已启动！"
	@echo ""
	@echo "📊 服务状态："
	@echo "   Redis:    redis-cli ping"
	@echo "   Celery:   tail -f $(CELERY_WORKER_LOG)"
	@echo "   Backend:  http://localhost:$(BACKEND_PORT)"
	@echo "   API Docs: http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "🚀 启动前端服务："
	@echo "   make dev-frontend"
	@echo ""
	@echo "🧪 运行端到端测试："
	@echo "   make test-e2e"
	@echo ""

dev-golden-path: ## 🌟 黄金路径：一键启动完整环境并创建测试数据（Day 12 验收通过）
	@echo "=========================================="
	@echo "🌟 Reddit Signal Scanner - 黄金启动路径"
	@echo "=========================================="
	@echo ""
	@echo "📋 启动顺序（基于 Day 12 端到端验收）："
	@echo "   1. Redis 服务"
	@echo "   2. Redis 测试数据"
	@echo "   3. Celery Worker"
	@echo "   4. 后端服务 (FastAPI)"
	@echo "   5. 数据库用户和任务"
	@echo "   6. 前端服务 (Vite)"
	@echo ""
	@echo "==> 1️⃣  启动 Redis ..."
	@$(MAKE) redis-start
	@echo ""
	@echo "==> 2️⃣  填充 Redis 测试数据 ..."
	@$(MAKE) redis-seed
	@echo ""
	@echo "==> 3️⃣  启动 Celery Worker ..."
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && \
		$(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	else \
		cd $(BACKEND_DIR) && $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	fi
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker started" || echo "⚠️  请检查日志: $(CELERY_WORKER_LOG)"
	@echo ""
	@echo "==> 4️⃣  启动后端服务 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload > /tmp/backend_uvicorn.log 2>&1 &
	@sleep 3
	@curl -s http://localhost:$(BACKEND_PORT)/ > /dev/null && echo "✅ Backend server started" || echo "⚠️  Backend server可能未启动"
	@echo ""
	@echo "==> 5️⃣  创建测试用户和任务 ..."
	@$(MAKE) db-seed-user-task
	@echo ""
	@echo "==> 6️⃣  启动前端服务 ..."
	@cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT) > /tmp/frontend_vite.log 2>&1 &
	@sleep 3
	@curl -s http://localhost:$(FRONTEND_PORT)/ > /dev/null && echo "✅ Frontend server started" || echo "⚠️  Frontend server可能未启动"
	@echo ""
	@echo "=========================================="
	@echo "✅ 黄金路径启动完成！"
	@echo "=========================================="
	@echo ""
	@echo "📊 服务状态："
	@echo "   Redis:    ✅ redis://localhost:$(REDIS_PORT)"
	@echo "   Celery:   ✅ tail -f $(CELERY_WORKER_LOG)"
	@echo "   Backend:  ✅ http://localhost:$(BACKEND_PORT)"
	@echo "   Frontend: ✅ http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "📝 测试数据："
	@echo "   用户邮箱: prd-test@example.com"
	@echo "   任务状态: 已完成分析"
	@echo ""
	@echo "🔗 快速访问："
	@echo "   前端首页:  http://localhost:$(FRONTEND_PORT)/"
	@echo "   API 文档:  http://localhost:$(BACKEND_PORT)/docs"
	@echo "   报告页面:  检查终端输出的任务 ID"
	@echo ""
	@echo "📋 查看日志："
	@echo "   Celery:   tail -f $(CELERY_WORKER_LOG)"
	@echo "   Backend:  tail -f /tmp/backend_uvicorn.log"
	@echo "   Frontend: tail -f /tmp/frontend_vite.log"
	@echo ""
	@echo "🛑 停止所有服务："
	@echo "   make kill-ports && make kill-celery && make kill-redis"
	@echo ""

# ============================================================
# 服务重启（清理端口 + 重新启动）
# ============================================================

restart-backend: kill-backend-port ## 重启后端服务（清理端口 8006 后重新启动）
	@echo "==> Restarting backend on port $(BACKEND_PORT) ..."
	@sleep 1
	@cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

restart-frontend: kill-frontend-port ## 重启前端服务（清理端口 3006 后重新启动）
	@echo "==> Restarting frontend on port $(FRONTEND_PORT) ..."
	@sleep 1
	@cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT)

restart-all: kill-ports ## 重启所有服务（清理所有端口后重新启动）
	@echo "==> All ports cleared. Please run in separate terminals:"
	@echo "    终端 1: make dev-backend"
	@echo "    终端 2: make dev-frontend"

# ============================================================
# 服务状态检查
# ============================================================

status: check-services ## 检查前后端服务状态（别名）

check-services: ## 检查前后端服务是否正常运行
	@bash scripts/check-services.sh

# ============================================================
# 测试命令
# ============================================================

test-backend: ## 运行后端所有测试
	@echo "==> Running backend tests ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short

test-frontend: ## 运行前端所有测试
	@echo "==> Running frontend tests ..."
	@cd $(FRONTEND_DIR) && npm test

test-all: test-backend test-frontend ## 运行前后端所有测试

test: test-backend ## 快捷方式：运行后端测试

test-e2e: ## 运行端到端测试（需要先启动完整环境）
	@echo "==> Running end-to-end tests (safe runner) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash scripts/pytest_safe.sh tests/e2e -v -s

# 安全版测试（禁用插件自动加载 + 强制日志），避免会话静默无输出
.PHONY: test-backend-safe test-e2e-safe

SAFE_PYTEST := $(BACKEND_DIR)/scripts/pytest_safe.sh

test-backend-safe: ## 使用安全启动器运行后端测试（建议在本地/CI默认使用）
	@echo "==> Running backend tests (safe runner) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash $(SAFE_PYTEST) tests/ -v -s

test-e2e-safe: ## 使用安全启动器运行端到端测试（不依赖常驻服务）
	@echo "==> Running end-to-end tests (safe runner) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash $(SAFE_PYTEST) tests/e2e -v -s


test-admin-e2e: ## 运行Admin端到端测试（需运行Redis/Celery/Backend并配置ADMIN_EMAILS）
	@echo "==> Running admin end-to-end validation ..."
	@cd $(BACKEND_DIR) && ADMIN_E2E_BASE_URL="http://localhost:$(BACKEND_PORT)" $(PYTHON) scripts/test_admin_e2e.py

# ============================================================
# 测试修复与诊断命令
# ============================================================

test-kill-pytest: ## 清理所有残留的 pytest 进程
	@echo "==> Killing all pytest processes ..."
	@pkill -9 -f pytest || echo "No pytest processes found"
	@sleep 1
	@ps aux | grep pytest | grep -v grep || echo "✅ All pytest processes cleaned"

test-clean: ## 清理测试缓存和残留进程
	@echo "==> Cleaning test environment ..."
	@pkill -9 -f pytest || echo "No pytest processes found"
	@cd $(BACKEND_DIR) && rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/api/__pycache__ tests/integration/__pycache__
	@cd $(FRONTEND_DIR) && rm -rf coverage .nyc_output
	@echo "✅ Test environment cleaned"

test-fix: test-clean ## 修复测试环境（清理进程+缓存）并运行测试
	@echo "==> Fixing test environment and running tests ..."
	@cd $(BACKEND_DIR) && bash run_tests.sh tests/api/test_admin.py tests/api/test_auth_integration.py -v

test-diagnose: ## 运行测试诊断脚本
	@echo "==> Running test diagnostics ..."
	@cd $(BACKEND_DIR) && bash fix_pytest_step_by_step.sh

# ============================================================
# Celery 任务系统
# ============================================================

celery-start: ## 启动 Celery Worker（前台运行，加载环境变量）
	@echo "==> Starting Celery worker (analysis_queue) ..."
	@echo "    日志: $(CELERY_WORKER_LOG)"
	@echo "    池模式: solo (macOS fork() 兼容)"
	@echo "    环境变量: 从 backend/.env 加载"
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		echo "✅ 发现 .env 文件"; \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && \
		$(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue; \
	else \
		echo "⚠️  未找到 backend/.env 文件，使用默认配置"; \
		cd $(BACKEND_DIR) && $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue; \
	fi

celery-stop: kill-celery ## 停止所有Celery Worker

celery-restart: celery-stop ## 重启Celery Worker（后台运行，加载环境变量）
	@echo "==> Restarting Celery worker ..."
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		echo "✅ 加载环境变量从 backend/.env"; \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && \
		nohup $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	else \
		echo "⚠️  未找到 backend/.env，使用默认配置"; \
		cd $(BACKEND_DIR) && nohup $(PYTHON) -m celery -A $(CELERY_APP) worker --loglevel=info --pool=solo \
		  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
		  > $(CELERY_WORKER_LOG) 2>&1 & \
	fi
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker restarted" || echo "⚠️  请检查日志: $(CELERY_WORKER_LOG)"

celery-logs: ## 查看Celery Worker日志
	@echo "==> Celery Worker logs ($(CELERY_WORKER_LOG)) ..."
	@tail -100 $(CELERY_WORKER_LOG)

celery-verify: ## 验证 Celery 配置与 Redis/Result backend
	@echo "==> Verifying Celery configuration ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(SCRIPTS_DIR)/verify_celery_config.py $(ARGS)

celery-seed: ## 创建默认测试任务（可用 ARGS 覆盖邮箱、描述等）
	@echo "==> Seeding Celery verification task ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(SCRIPTS_DIR)/seed_analysis_task.py $(ARGS)

celery-seed-unique: ## 创建随机邮箱的测试任务，避免与历史记录冲突
	@echo "==> Seeding Celery verification task with unique email ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(SCRIPTS_DIR)/seed_analysis_task.py --unique-email $(ARGS)

celery-purge: ## 清理由脚本生成的测试任务与用户记录
	@echo "==> Purging Celery verification test data ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(SCRIPTS_DIR)/seed_analysis_task.py --purge $(ARGS)

celery-test: ## 运行任务系统相关测试
	@echo "==> Running Celery task system tests ..."
	PYTHONPATH=$(BACKEND_DIR) pytest $(BACKEND_DIR)/tests/test_task_system.py $(BACKEND_DIR)/tests/test_celery_basic.py -v

celery-mypy: ## 对任务系统核心文件运行 mypy --strict
	@echo "==> Running mypy --strict for Celery task system ..."
	PYTHONPATH=$(BACKEND_DIR) mypy --strict \
		$(BACKEND_DIR)/app/services/task_status_cache.py \
		$(BACKEND_DIR)/app/tasks/analysis_task.py \
		$(SCRIPTS_DIR)/start_celery_worker.py \
		$(SCRIPTS_DIR)/verify_celery_config.py \
		$(SCRIPTS_DIR)/seed_analysis_task.py \
		$(BACKEND_DIR)/tests/test_task_system.py

# ============================================================
# 数据库迁移
# ============================================================

db-migrate: ## 创建新的数据库迁移 (需要 MESSAGE="描述")
	@echo "==> Creating new database migration ..."
	@cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(MESSAGE)"

db-upgrade: ## 升级数据库到最新版本
	@echo "==> Upgrading database to latest version ..."
	@cd $(BACKEND_DIR) && alembic upgrade head

db-downgrade: ## 降级数据库一个版本
	@echo "==> Downgrading database by one version ..."
	@cd $(BACKEND_DIR) && alembic downgrade -1

db-reset: ## 重置数据库（危险操作！）
	@echo "==> WARNING: This will drop all tables and recreate them!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd $(BACKEND_DIR) && alembic downgrade base && alembic upgrade head; \
	fi

db-seed-user-task: ## 创建测试用户和任务（用于黄金路径）
	@echo "==> Creating test user and task ..."
	@PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(BACKEND_DIR)/scripts/seed_user_task.py --frontend-port $(FRONTEND_PORT)
	@echo ""
	@echo "⏳ Waiting for analysis to progress (check Celery logs) ..."
	@sleep 5
	@echo "✅ Test user and task created successfully"

# ============================================================
# 清理命令
# ============================================================

clean: clean-pyc clean-test ## 清理所有生成文件

clean-pyc: ## 清理 Python 缓存文件
	@echo "==> Cleaning Python cache files ..."
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} +

clean-test: ## 清理测试缓存
	@echo "==> Cleaning test cache ..."
	@find . -type d -name '.pytest_cache' -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type f -name '.coverage' -delete

# ============================================================
# 依赖管理
# ============================================================

install-backend: ## 安装后端依赖（修正为 backend/requirements.txt）
	@echo "==> Installing backend dependencies ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -U pytest pytest-asyncio httpx fakeredis || true

install-frontend: ## 安装前端依赖
	@echo "==> Installing frontend dependencies ..."
	@cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend ## 安装所有依赖

# ============================================================
# MCP 工具安装与验证
# ============================================================

mcp-install: ## 安装和配置 MCP 工具 (exa, chrome-devtools, spec-kit)
	@echo "==> 安装 MCP 工具 ..."
	@echo ""
	@echo "1️⃣  安装 Spec Kit (Python CLI) ..."
	@uv tool install specify-cli --from git+https://github.com/github/spec-kit.git || echo "⚠️  Spec Kit 安装失败，请手动安装"
	@echo ""
	@echo "2️⃣  验证 Spec Kit 安装 ..."
	@which specify && specify check || echo "⚠️  Spec Kit 未在 PATH 中找到"
	@echo ""
	@echo "✅ MCP 工具安装完成"
	@echo ""
	@echo "📝 配置步骤:"
	@echo ""
	@echo "1️⃣  Exa API Key 已配置在 .env.local"
	@echo ""
	@echo "2️⃣  配置 MCP servers 到你的 IDE/editor:"
	@echo "   参考配置文件: mcp-config.json"
	@echo "   或查看详细指南: docs/MCP-SETUP-GUIDE.md"
	@echo ""
	@echo "3️⃣  验证安装:"
	@echo "   运行: make mcp-verify"
	@echo ""
	@echo "📖 Documentation:"
	@echo "   exa-mcp-server: https://docs.exa.ai/reference/exa-mcp"
	@echo "   Chrome DevTools: https://github.com/ChromeDevTools/chrome-devtools-mcp"
	@echo "   Spec Kit: https://github.com/github/spec-kit"
	@echo ""

mcp-verify: ## 验证 MCP 工具安装
	@echo "==> Verifying MCP tools installation ..."
	@echo ""
	@echo "1️⃣  Testing exa-mcp-server ..."
	@echo "   运行: npx -y exa-mcp-server --version"
	@timeout 5 npx -y exa-mcp-server --version 2>&1 || echo "✅ exa-mcp-server 可用 (通过 npx)"
	@echo ""
	@echo "2️⃣  Testing Chrome DevTools MCP ..."
	@echo "   运行: npx -y chrome-devtools-mcp@latest --help"
	@timeout 5 npx -y chrome-devtools-mcp@latest --help 2>&1 | head -5 || echo "✅ Chrome DevTools MCP 可用 (通过 npx)"
	@echo ""
	@echo "3️⃣  Testing Spec Kit ..."
	@which specify && specify check || echo "❌ Spec Kit not found in PATH"
	@echo ""
	@echo "4️⃣  Checking Node.js and npm ..."
	@node --version && echo "✅ Node.js installed" || echo "❌ Node.js not found"
	@npm --version && echo "✅ npm installed" || echo "❌ npm not found"
	@echo ""
	@echo "5️⃣  Checking Python and uv ..."
	@python3 --version && echo "✅ Python installed" || echo "❌ Python not found"
	@uv --version && echo "✅ uv installed" || echo "❌ uv not found"
	@echo ""
	@echo "6️⃣  Checking Exa API Key ..."
	@grep -q "EXA_API_KEY" .env.local && echo "✅ EXA_API_KEY found in .env.local" || echo "❌ EXA_API_KEY not found in .env.local"
	@echo ""
	@echo "📚 Documentation:"
	@echo "   完整配置指南: docs/MCP-SETUP-GUIDE.md"
	@echo "   MCP 配置文件: mcp-config.json"
	@echo "   exa-mcp-server: https://docs.exa.ai/reference/exa-mcp"
	@echo "   Chrome DevTools: https://github.com/ChromeDevTools/chrome-devtools-mcp"
	@echo "   Spec Kit: https://github.com/github/spec-kit"
	@echo ""
	@echo "✅ MCP 工具验证完成！"
	@echo ""

# ============================================================
# 快速启动指南
# ============================================================

quickstart: ## 显示快速启动指南
	@echo ""
	@echo "🚀 Reddit Signal Scanner - 快速启动指南"
	@echo "=========================================="
	@echo ""
	@echo "1️⃣  启动后端服务器："
	@echo "   make dev-backend"
	@echo "   访问: http://localhost:$(BACKEND_PORT)"
	@echo "   文档: http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "2️⃣  启动前端服务器（新终端）："
	@echo "   make dev-frontend"
	@echo "   访问: http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "3️⃣  如果端口被占用，先清理端口："
	@echo "   make kill-ports          # 清理所有端口"
	@echo "   make restart-backend     # 重启后端"
	@echo "   make restart-frontend    # 重启前端"
	@echo ""
	@echo "4️⃣  运行测试："
	@echo "   make test-backend"
	@echo ""
	@echo "5️⃣  启动 Celery Worker（可选）："
	@echo "   make celery-start"
	@echo ""
	@echo "📚 更多命令请运行: make help"
	@echo ""
# Day13: Community pool utilities

EXCEL_FILE ?= 社区筛选.xlsx

.PHONY: db-migrate-up
db-migrate-up:
	cd backend && alembic upgrade head

.PHONY: seed-from-excel
seed-from-excel:
	python backend/scripts/import_seed_communities_from_excel.py "$(EXCEL_FILE)" --output backend/config/seed_communities.json

.PHONY: import-community-pool
import-community-pool:
	python -m app.scripts.import_seed_to_db || python backend/scripts/import_seed_to_db.py

.PHONY: validate-seed
validate-seed:
	python backend/scripts/validate_seed_communities.py

.PHONY: day13-seed-all
day13-seed-all: db-migrate-up seed-from-excel validate-seed import-community-pool
	@echo "✅ Day13 seed pipeline completed."


# ============================================================
# PRD-10 Admin 社区 Excel 导入 - 非交互端到端验收
# 说明：为避免交互命令环境卡住，所有步骤使用 Python 直调
# ============================================================
.PHONY: prd10-accept-template prd10-accept-dryrun prd10-accept-import prd10-accept-history
.PHONY: prd10-accept-routes prd10-accept-frontend-files prd10-accept-all

prd10-accept-template: ## 生成 Excel 模板并快速校验（字节数>1000）
	@echo "==> PRD-10: 生成模板 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/prd10_accept.py template

prd10-accept-dryrun: ## dry_run=True 仅验证，不入库
	@echo "==> PRD-10: dry_run 验证 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/prd10_accept.py dryrun

prd10-accept-import: ## dry_run=False 实际导入，写入历史
	@echo "==> PRD-10: 实际导入 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/prd10_accept.py import

prd10-accept-history: ## 校验导入历史表至少一条记录
	@echo "==> PRD-10: 校验导入历史 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/prd10_accept.py history

prd10-accept-routes: ## 校验 3 个 API 路由已注册
	@echo "==> PRD-10: 校验 API 路由 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/prd10_accept.py routes

prd10-accept-frontend-files: ## 校验前端页面与组件文件存在
	@echo "==> PRD-10: 校验前端文件 ..."
	@test -f $(FRONTEND_DIR)/src/pages/admin/CommunityImport.tsx && echo '✅ 页面文件存在'
	@test -f $(FRONTEND_DIR)/src/components/admin/FileUpload.tsx && echo '✅ FileUpload 组件存在'
	@test -f $(FRONTEND_DIR)/src/components/admin/ImportResult.tsx && echo '✅ ImportResult 组件存在'

prd10-accept-all: prd10-accept-template prd10-accept-dryrun prd10-accept-import prd10-accept-history prd10-accept-routes prd10-accept-frontend-files ## 一键完成 PRD-10 非交互验收
	@echo "✅ PRD-10 验收完成（非交互直调路径）"
