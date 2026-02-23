# Development server orchestration and golden path helpers

.PHONY: dev-backend dev-frontend dev-all dev-full dev-real dev-golden-path quickstart crawl-once crawl-crossborder crawl-seeds
.PHONY: crawler-dryrun

dev-backend: ## 启动后端开发服务器 (FastAPI + Uvicorn, 端口 8006, 启用Celery dispatch)
	@echo "==> Starting backend development server on http://localhost:$(BACKEND_PORT) ..."
	@echo "    API Docs: http://localhost:$(BACKEND_PORT)/docs"
	@echo "    OpenAPI JSON: http://localhost:$(BACKEND_PORT)/openapi.json"
	@echo "    ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH)"
	@bash -lc '. $(COMMON_SH); require_backend_env; run_backend_dev'

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
	@echo "3️⃣  启动抓取系统（Beat + patrol + bulk）..."
	@$(MAKE) crawl-start
	@echo ""
	@echo "4️⃣  启动分析 Worker（analysis_queue）..."
	@$(MAKE) start-worker-analysis
	@sleep 3
	@tail -20 logs/celery_analysis.log | grep "ready" && echo "✅ Analysis Worker started" || echo "⚠️  Analysis Worker可能未启动，请检查 logs/celery_analysis.log"
	@echo ""
	@echo "5️⃣  启动后端服务（后台）..."
	@bash -lc '. $(COMMON_SH); start_backend_background'
	@sleep 3
	@bash -lc '. $(COMMON_SH); if check_backend_health; then echo "✅ Backend server started"; else echo "⚠️  Backend server可能未启动"; fi'
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
	@echo "==> 启动真实 Reddit 本地验收环境 ..."
	@echo ""
	@echo "1️⃣  启动 Redis ..."
	@$(MAKE) redis-start
	@echo ""
	@echo "2️⃣  启动抓取系统（Beat + patrol + bulk）..."
	@$(MAKE) crawl-start
	@echo ""
	@echo "3️⃣  启动分析 Worker（analysis_queue）..."
	@$(MAKE) start-worker-analysis
	@sleep 3
	@tail -20 logs/celery_analysis.log | grep "ready" && echo "✅ Analysis Worker started" || echo "⚠️  请检查 logs/celery_analysis.log"
	@echo ""
	@echo "4️⃣  启动后端服务 ..."
	@bash -lc '. $(COMMON_SH); start_backend_background'
	@sleep 3
	@bash -lc '. $(COMMON_SH); if check_backend_health; then echo "✅ Backend server started"; else echo "⚠️  Backend server可能未启动"; fi'
	@echo ""
	@echo "5️⃣  （可选）启动前端服务 ..."
	@bash -lc '. $(COMMON_SH); start_frontend_background'
	@sleep 3
	@bash -lc '. $(COMMON_SH); if check_frontend_health; then echo "✅ Frontend server started"; else echo "⚠️  Frontend server可能未启动"; fi'
	@echo ""
	@echo "✅ 真实 Reddit 本地验收环境已就绪（未注入任何测试/Mock 数据）"
	@echo "   注意：请确保 backend/.env 已设置 REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET"
	@echo ""

dev-golden-path: ## 🌟 黄金路径：一键启动完整环境并创建测试数据（Day 12 验收通过）
	@bash scripts/dev_golden_path.sh

crawl-crossborder: ## 使用当前社区池执行增量抓取（不刷新、不合并；隔离模式推荐）
	@echo "==> 使用当前社区池执行增量抓取（不 force-refresh，隔离模式） ..."
	@cd $(BACKEND_DIR) && DISABLE_TOP1000_BASELINE=1 PYTHONPATH=. $(PYTHON) scripts/trigger_incremental_crawl.py || true
	@echo "✅ 已按隔离模式触发增量抓取；使用 'make celery-logs' 查看进度"

crawl-once: ## 从 crawler.yml 读取并抓取一次（按 SCOPE=T1|T2|T3|all，可加 FORCE=1）
	@SCOPE=$${SCOPE:-T1}; FORCE=$${FORCE:-0}; \
	 echo "==> crawl-once scope=$$SCOPE force=$$FORCE ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/crawl_once.py --scope $$SCOPE $$( [ "$$FORCE" = "1" ] && echo "--force-refresh" )
	@echo "✅ 结果请查看 reports/local-acceptance/crawl-once-*.json"

crawl-seeds: ## 种子池抓取入口（等同 crawl-once，默认 SCOPE=T1）
	@SCOPE=$${SCOPE:-T1}; FORCE=$${FORCE:-0}; \
	 echo "==> crawl-seeds scope=$$SCOPE force=$$FORCE (alias of crawl-once) ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/crawl_once.py --scope $$SCOPE $$( [ "$$FORCE" = "1" ] && echo "--force-refresh" )
	@echo "✅ 结果请查看 reports/local-acceptance/crawl-once-*.json"

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
