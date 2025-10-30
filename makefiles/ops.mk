# Operational helpers: restart services, health checks

.PHONY: restart-backend restart-frontend restart-all status check-services

restart-backend: kill-backend-port ## 重启后端服务（清理端口 8006 后重新启动）
	@echo "==> Restarting backend on port $(BACKEND_PORT) ..."
	@sleep 1
	@. $(COMMON_SH)
	@run_backend_dev

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
