# Celery worker management

.PHONY: celery-start celery-stop celery-restart celery-logs celery-verify celery-seed celery-seed-unique celery-purge
.PHONY: celery-test celery-mypy

celery-start: ## 启动 Celery Worker（前台运行，默认 analysis_queue）
	@echo "==> Starting Celery worker (default: analysis_queue) ..."
	@echo "    日志: $(CELERY_WORKER_LOG)"
	@echo "    池模式: solo (macOS fork() 兼容)"
	@echo "    环境变量: 从 backend/.env 加载"
	@bash -lc '. $(COMMON_SH); require_backend_env; CELERY_QUEUES="$${CELERY_QUEUES:-analysis_queue}" start_celery_worker foreground'

celery-stop: ## 停止所有Celery Worker
	@echo "==> Stopping Celery workers ..."
	@bash -lc '. $(COMMON_SH); stop_celery_worker'
	@sleep 1

celery-restart: celery-stop ## 重启Celery Worker（后台运行，默认 analysis_queue）
	@echo "==> Restarting Celery worker ..."
	@bash -lc '. $(COMMON_SH); require_backend_env; CELERY_QUEUES="$${CELERY_QUEUES:-analysis_queue}" start_celery_worker background'
	@sleep 3
	@tail -20 $(CELERY_WORKER_LOG) | grep "ready" && echo "✅ Celery Worker restarted" || echo "⚠️  请检查日志: $(CELERY_WORKER_LOG)"

celery-logs: ## 查看Celery Worker日志
	@echo "==> Celery Worker logs ($(CELERY_WORKER_LOG)) ..."
	@tail -100 $(CELERY_WORKER_LOG)

celery-verify: ## 验证 Celery 配置与 Redis/Result backend
	@echo "==> Verifying Celery configuration ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(BACKEND_DIR)/scripts/verify_celery_config.py $(ARGS)

celery-seed: ## 创建默认测试任务（固定用户+随机任务ID）
	@echo "==> Seeding Celery verification task ..."
	PYTHONPATH=$(BACKEND_DIR) $(PYTHON) $(BACKEND_DIR)/scripts/seed_user_task.py

celery-seed-unique: ## 兼容入口：等同 celery-seed（任务ID已随机）
	@$(MAKE) celery-seed

celery-purge: ## 清理测试数据（仅 test/dev；需显式确认）
	@echo "==> Purging local/test data (requires CLEANUP_CONFIRM=1) ..."
	@CLEANUP_CONFIRM=$${CLEANUP_CONFIRM:-0} $(SCRIPTS_DIR)/cleanup_test_data.sh

celery-test: ## 运行任务系统相关测试
	@echo "==> Running Celery task system tests ..."
	PYTHONPATH=$(BACKEND_DIR) pytest $(BACKEND_DIR)/tests/test_task_system.py $(BACKEND_DIR)/tests/test_celery_basic.py -v

celery-mypy: ## 对任务系统核心文件运行 mypy --strict
	@echo "==> Running mypy --strict for Celery task system ..."
	PYTHONPATH=$(BACKEND_DIR) mypy --strict \
		$(BACKEND_DIR)/app/services/task_status_cache.py \
		$(BACKEND_DIR)/app/tasks/analysis_task.py \
		$(BACKEND_DIR)/scripts/verify_celery_config.py \
		$(BACKEND_DIR)/scripts/check_celery_health.py \
		$(BACKEND_DIR)/scripts/seed_user_task.py \
		$(BACKEND_DIR)/tests/test_task_system.py

# ---- Spec013: 便捷启动 Celery Beat（含 Worker）----
.PHONY: dev-celery-beat
dev-celery-beat: ## 启动 Celery Beat + Worker（后台），日志输出到 backend/tmp
	@echo "==> Starting Celery Beat + Worker (background) ..."
	@$(MAKE) crawl-start
	@echo "✅ Celery Beat/Worker 已启动（走 smart crawler 流程）。"
