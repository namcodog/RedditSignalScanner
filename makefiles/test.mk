# Test targets and diagnostics

SAFE_PYTEST := $(BACKEND_DIR)/scripts/pytest_safe.sh

.PHONY: test test-all test-backend test-frontend test-e2e test-admin-e2e test-contract test-tasks-smoke
.PHONY: test-backend-safe test-e2e-safe clean-e2e-snapshots test-clean test-fix test-diagnose test-kill-pytest

test-backend: ## 运行后端所有测试
	@echo "==> Running backend tests ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short

test-frontend: ## 运行前端所有测试
	@echo "==> Running frontend tests ..."
	@cd $(FRONTEND_DIR) && npm test

test-all: test-backend test-frontend ## 运行前后端所有测试

test: test-backend ## 快捷方式：运行后端测试

test-e2e: ## 运行端到端测试（需要先启动完整环境）- 只运行关键路径测试
	@echo "==> Running critical path E2E tests (target: < 5 minutes) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash scripts/pytest_safe.sh tests/e2e/test_critical_path.py -v -s

test-tasks-smoke: ## 运行后台维护/监控任务的快速巡检测试
	@echo "==> Running maintenance & monitoring smoke tests ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/tasks/test_tasks_smoke.py -q

test-backend-safe: ## 使用安全启动器运行后端测试（建议在本地/CI默认使用）
	@echo "==> Running backend tests (safe runner) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash $(SAFE_PYTEST) tests/ -v -s

test-e2e-safe: ## 使用安全启动器运行端到端测试（不依赖常驻服务）
	@echo "==> Running end-to-end tests (safe runner) ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash $(SAFE_PYTEST) tests/e2e -v -s

clean-e2e-snapshots: ## 清理 E2E 失败快照
	@echo "==> Cleaning E2E failure snapshots ..."
	@rm -rf reports/failed_e2e/*
	@echo "==> E2E snapshots cleaned."

test-contract: ## 运行 API 契约测试（schema 验证 + breaking changes 检测）
	@echo "==> Running API contract tests ..."
	@echo ""
	@echo "📝 Step 1: 检测 Breaking Changes"
	@cd $(BACKEND_DIR) && python scripts/check_breaking_changes.py
	@echo ""
	@echo "✅ API 契约测试完成"
	@echo ""
	@echo "💡 提示: Property-based 测试（schemathesis）需要较长时间，已跳过"
	@echo "   如需运行完整测试，请执行: cd backend && python scripts/test_contract.py"

test-admin-e2e: ## 运行Admin端到端测试（需运行Redis/Celery/Backend并配置ADMIN_EMAILS）
	@echo "==> Running admin end-to-end validation ..."
	@cd $(BACKEND_DIR) && ADMIN_E2E_BASE_URL="http://localhost:$(BACKEND_PORT)" $(PYTHON) scripts/test_admin_e2e.py

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
