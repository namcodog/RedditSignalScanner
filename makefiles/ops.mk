# Operational helpers: restart services, health checks

.PHONY: restart-backend restart-frontend restart-all status check-services posts-growth-7d celery-meta-count pipeline-health autoheal-start

restart-backend: kill-backend-port ## 重启后端服务（清理端口 8006 后重新启动）
	@echo "==> Restarting backend on port $(BACKEND_PORT) ..."
	@sleep 1
	@bash -lc '. $(COMMON_SH); run_backend_dev'

restart-frontend: kill-frontend-port ## 重启前端服务（清理端口 3006 后重新启动）
	@echo "==> Restarting frontend on port $(FRONTEND_PORT) ..."
	@sleep 1
	@cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT)

restart-all: kill-ports ## 重启所有服务（清理所有端口后提供手动指引）
	@echo "==> All ports cleared. Please run in separate terminals:"
	@echo "    终端 1: make dev-backend"
	@echo "    终端 2: make dev-frontend"

status: check-services ## 检查前后端服务状态（别名）

check-services: ## 检查前后端服务是否正常运行
	@bash scripts/check-services.sh

posts-growth-7d: ## 打印最近7天 posts_hot 按天计数（CSV）
	@echo "==> posts_hot growth (last 7 days) ..."
	@PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(BACKEND_DIR)/scripts/posts_growth_7d.py

celery-meta-count: ## 统计 Redis 中 celery-task-meta-* 数量（用于确认任务执行）
	@echo "==> Counting celery-task-meta-* in Redis (db0..db5) ..."
	@for DB in 0 1 2 3 4 5; do \
	  C=$$(redis-cli -n $$DB --scan --pattern 'celery-task-meta-*' | wc -l | tr -d ' '); \
	  echo "db$$DB: $$C"; \
	done

pipeline-health: ## 生成端到端运行快照（Beat/Pool/Posts/Redis/Beat配置）
	@bash scripts/pipeline_health_snapshot.sh

autoheal-start: ## 启动本地自愈守护（每60s体检 Celery，失败自动重启 Beat+Worker）
	@echo "==> Starting auto-heal daemon (logs: reports/local-acceptance/autoheal.log) ..."
	@nohup bash scripts/autoheal.sh >/dev/null 2>&1 & echo $! > /tmp/rss-autoheal.pid && echo "PID: $$(cat /tmp/rss-autoheal.pid)"
