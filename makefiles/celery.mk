# Celery worker management

.PHONY: celery-start celery-stop celery-restart celery-logs celery-verify celery-seed celery-seed-unique celery-purge
.PHONY: celery-test celery-mypy

celery-start: ## 启动 Celery Worker（前台运行，加载环境变量）
	@. $(COMMON_SH)
	@echo "==> Starting Celery worker (analysis_queue) ..."
	@echo "    日志: $(CELERY_WORKER_LOG)"
	@echo "    池模式: solo (macOS fork() 兼容)"
	@echo "    环境变量: 从 backend/.env 加载"
	@require_backend_env
	@start_celery_worker foreground

celery-stop: ## 停止所有Celery Worker
	@. $(COMMON_SH)
	@echo "==> Stopping Celery workers ..."
	@stop_celery_worker
	@sleep 1

celery-restart: celery-stop ## 重启Celery Worker（后台运行，加载环境变量）
	@. $(COMMON_SH)
	@echo "==> Restarting Celery worker ..."
	@require_backend_env
	@start_celery_worker background
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
