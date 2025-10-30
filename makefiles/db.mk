# Database migration utilities

.PHONY: db-migrate db-upgrade db-downgrade db-reset db-seed-user-task

db-migrate: ## 创建新的数据库迁移 (需要 MESSAGE="描述")
	@echo "==> Creating new database migration ..."
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && alembic revision --autogenerate -m "$(MESSAGE)"; \
	else \
		cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(MESSAGE)"; \
	fi

db-upgrade: ## 升级数据库到最新版本
	@echo "==> Upgrading database to latest version ..."
	@if [ ! -f $(BACKEND_DIR)/.env ] && [ -z "$$DATABASE_URL" ]; then \
		echo "❌ DATABASE_URL 未设置。请在环境变量或 backend/.env 中配置后再执行。"; \
		exit 1; \
	fi
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && alembic upgrade head; \
	else \
		cd $(BACKEND_DIR) && alembic upgrade head; \
	fi

db-downgrade: ## 降级数据库一个版本
	@echo "==> Downgrading database by one version ..."
	@if [ -f $(BACKEND_DIR)/.env ]; then \
		cd $(BACKEND_DIR) && export $$(cat .env | grep -v '^#' | xargs) && alembic downgrade -1; \
	else \
		cd $(BACKEND_DIR) && alembic downgrade -1; \
	fi

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
