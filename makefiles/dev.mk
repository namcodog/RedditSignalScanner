# Development server orchestration and golden path helpers

.PHONY: dev-backend dev-frontend dev-all dev-full dev-real dev-golden-path crawl-seeds quickstart

dev-backend: ## 启动后端开发服务器 (FastAPI + Uvicorn, 端口 8006, 启用Celery dispatch)
	@. $(COMMON_SH)
	@echo "==> Starting backend development server on http://localhost:$(BACKEND_PORT) ..."
	@echo "    API Docs: http://localhost:$(BACKEND_PORT)/docs"
	@echo "    OpenAPI JSON: http://localhost:$(BACKEND_PORT)/openapi.json"
	@echo "    ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH)"
	@require_backend_env
	@run_backend_dev

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
	@. $(COMMON_SH)
	@echo "==> 启动完整开发环境 ..."
	@echo ""
	@echo "1️⃣  启动Redis ..."
	@$(MAKE) redis-start
	@echo ""
	@echo "2️⃣  填充测试数据 ..."
	@$(MAKE) redis-seed
	@echo ""
	@echo "3️⃣  启动Celery Worker（后台）..."
	@require_backend_env
	@start_celery_worker background
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker started" || echo "⚠️  Celery Worker可能未启动，请检查日志: $(CELERY_WORKER_LOG)"
	@echo ""
	@echo "4️⃣  启动后端服务（后台）..."
	@start_backend_background
	@sleep 3
	@if check_backend_health; then \
		echo "✅ Backend server started"; \
	else \
		echo "⚠️  Backend server可能未启动"; \
	fi
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

dev-real: ## 启动真实 Reddit 验收环境（不注入任何 mock/seed 数据）
	@. $(COMMON_SH)
	@echo "==> 启动真实 Reddit 本地验收环境 ..."
	@echo ""
	@echo "1️⃣  启动 Redis ..."
	@$(MAKE) redis-start
	@echo ""
	@echo "2️⃣  启动 Celery Worker（后台）..."
	@require_backend_env
	@start_celery_worker background
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker started" || echo "⚠️  请检查日志: $(CELERY_WORKER_LOG)"
	@echo ""
	@echo "3️⃣  启动后端服务 ..."
	@start_backend_background
	@sleep 3
	@if check_backend_health; then \
		echo "✅ Backend server started"; \
	else \
		echo "⚠️  Backend server可能未启动"; \
	fi
	@echo ""
	@echo "4️⃣  （可选）启动前端服务 ..."
	@start_frontend_background
	@sleep 3
	@if check_frontend_health; then \
		echo "✅ Frontend server started"; \
	else \
		echo "⚠️  Frontend server可能未启动"; \
	fi
	@echo ""
	@echo "✅ 真实 Reddit 本地验收环境已就绪（未注入任何测试/Mock 数据）"
	@echo "   注意：请确保 backend/.env 已设置 REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET"
	@echo ""

dev-golden-path: ## 🌟 黄金路径：一键启动完整环境并创建测试数据（Day 12 验收通过）
	@bash scripts/dev_golden_path.sh

crawl-seeds: ## 触发种子社区真实爬取（需要 Celery 与 Backend 已启动）
	@echo "==> 触发爬取种子社区（真实 Reddit API） ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/trigger_initial_crawl.py --force-refresh || true
	@echo "✅ 批量爬取任务已触发；使用 'make celery-logs' 查看进度"

crawl-seeds-incremental: ## 触发种子社区增量爬取（冷热双写 + 水位线）
	@echo "==> 触发增量爬取（冷热双写 + 水位） ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/trigger_incremental_crawl.py --force-refresh || true
	@echo "✅ 增量爬取任务已触发；使用 'make celery-logs' 查看进度"

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
