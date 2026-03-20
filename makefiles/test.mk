# Test targets and diagnostics

SAFE_PYTEST := $(BACKEND_DIR)/scripts/pytest_safe.sh
PLAYWRIGHT_FORMAL_SPECS := e2e/user-journey.spec.ts e2e/report-page-simple.spec.ts e2e/product-polish-smoke.spec.ts e2e/admin-dashboard.spec.ts e2e/performance.spec.ts
PLAYWRIGHT_FLAGS ?= --project=chromium --reporter=line --workers=1
LIVE_REPORT_BULK_QUEUE_LIST ?= backfill_posts_queue_v2,backfill_queue,compensation_queue
LIVE_REPORT_ACCEPTANCE_ARGS ?= --required-tier A_full --max-analysis-attempts 3 --warmup-wait-timeout-seconds 420
TOPIC_PROFILE_MATRIX_ACCEPTANCE_ARGS ?=
LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS ?= 90
LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS ?= 300
LIVE_REPORT_BACKFILL_SETTLE_SECONDS ?= 20
LIVE_REPORT_BACKFILL_MAX_TARGETS ?= 120
LIVE_REPORT_REQUIRED_RUNS ?= 5
LIVE_REPORT_BACKLOG_STALE_MINUTES ?= 45
LIVE_REPORT_MAX_STALE_TASK_OUTBOX_PENDING ?= 120
LIVE_REPORT_MAX_STALE_CRAWLER_TARGETS_NOT_ENQUEUED ?= 200
LIVE_REPORT_PREFLIGHT_ARGS ?= --strict --stale-minutes $(LIVE_REPORT_BACKLOG_STALE_MINUTES) --max-stale-task-outbox-pending $(LIVE_REPORT_MAX_STALE_TASK_OUTBOX_PENDING) --max-stale-crawler-targets-not-enqueued $(LIVE_REPORT_MAX_STALE_CRAWLER_TARGETS_NOT_ENQUEUED)

.PHONY: test test-all test-backend test-frontend test-e2e test-e2e-formal test-e2e-smoke test-e2e-backend test-e2e-live-report test-e2e-live-report-5x test-e2e-live-report-preflight test-e2e-live-report-unblock-locks-dryrun test-e2e-live-report-unblock-locks-apply test-e2e-live-report-cleanup-dryrun test-e2e-live-report-cleanup-apply test-e2e-topic-profile-matrix demo-live-a-full test-admin-e2e test-contract test-tasks-smoke
.PHONY: test-backend-safe test-e2e-safe clean-e2e-snapshots test-clean test-fix test-diagnose test-kill-pytest

test-backend: ## 运行后端所有测试
	@echo "==> Running backend tests ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short

test-frontend: ## 运行前端所有测试
	@echo "==> Running frontend tests ..."
	@cd $(FRONTEND_DIR) && npm test

test-all: test-backend test-frontend ## 运行前后端所有测试

test: test-backend ## 快捷方式：运行后端测试

test-e2e: test-e2e-formal ## 运行当前正式前端 E2E 套件（Playwright）

test-e2e-formal: ## 运行当前正式前端 E2E 套件（Playwright）
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@echo "==> Running current-world frontend E2E suite ..."
	@cd $(FRONTEND_DIR) && npx playwright test $(PLAYWRIGHT_FORMAL_SPECS) $(PLAYWRIGHT_FLAGS)

test-e2e-smoke: ## 运行产品打磨 smoke E2E
	@echo "==> Running product polish smoke E2E ..."
	@cd $(FRONTEND_DIR) && npx playwright test e2e/product-polish-smoke.spec.ts $(PLAYWRIGHT_FLAGS)

test-e2e-backend: ## 运行旧后端关键链路 E2E（pytest）
	@echo "==> Running backend critical-path E2E ..."
	@cd $(BACKEND_DIR) && APP_ENV=test ENABLE_CELERY_DISPATCH=0 bash scripts/pytest_safe.sh tests/e2e/test_critical_path.py -v -s

test-e2e-live-report-preflight: ## live report 验收前置门禁（队列积压）
	@echo "==> Running live report preflight gate ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/live_report_preflight_gate.py $(LIVE_REPORT_PREFLIGHT_ARGS)

test-e2e-live-report-unblock-locks-dryrun: ## 检查 live 验收相关数据库锁阻塞（dry-run）
	@echo "==> Inspecting stale lock blockers ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/unblock_live_acceptance_locks.py

test-e2e-live-report-unblock-locks-apply: ## 清理 live 验收相关数据库锁阻塞（apply）
	@echo "==> Terminating stale lock blockers ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/unblock_live_acceptance_locks.py --apply

test-e2e-live-report-cleanup-dryrun: ## live report 验收清淤（dry-run）
	@echo "==> Dry-run stale backlog cleanup ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/cleanup_live_acceptance_backlog.py --stale-minutes $(LIVE_REPORT_BACKLOG_STALE_MINUTES)

test-e2e-live-report-cleanup-apply: ## live report 验收清淤（apply）
	@echo "==> Applying stale backlog cleanup ..."
	@$(MAKE) test-e2e-live-report-unblock-locks-apply
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/cleanup_live_acceptance_backlog.py --stale-minutes $(LIVE_REPORT_BACKLOG_STALE_MINUTES) --apply

test-e2e-live-report: ## 运行实时 report 真链路验收（登录->分析->状态->报告）
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@echo "==> Checking backend health ..."
	@curl -s http://localhost:$(BACKEND_PORT)/api/healthz >/dev/null || (echo "❌ 后端未运行，请先启动 backend（make dev-backend 或 make dev-real）" && exit 1)
	@$(MAKE) test-e2e-live-report-preflight
	@echo "==> Resetting Celery workers + pending broker backlog for deterministic acceptance ..."
	@$(MAKE) crawl-stop >/dev/null || true
	@pkill -9 -f "celery.*app.core.celery_app" >/dev/null 2>&1 || true
	@sleep 2
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app purge -f >/dev/null || true
	@echo "==> Starting isolated analysis worker ..."
	@mkdir -p logs
	@cd $(BACKEND_DIR) && DISABLE_AUTO_CRAWL_BOOTSTRAP=1 \
		WARMUP_AUTO_RERUN_BASE_DELAY_SECONDS="$(LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS)" \
		WARMUP_AUTO_RERUN_MAX_DELAY_SECONDS="$(LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS)" \
		WARMUP_INLINE_BACKFILL_SETTLE_SECONDS="$(LIVE_REPORT_BACKFILL_SETTLE_SECONDS)" \
		WARMUP_INLINE_BACKFILL_MAX_TARGETS="$(LIVE_REPORT_BACKFILL_MAX_TARGETS)" \
		celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=2 --queues=analysis_queue --hostname=analysis-live@%h >> ../logs/celery_analysis_live.log 2>&1 &
	@echo "==> Starting isolated bulk worker (live acceptance queues only) ..."
	@cd $(BACKEND_DIR) && DISABLE_AUTO_CRAWL_BOOTSTRAP=1 celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=$${BULK_WORKER_CONCURRENCY:-2} --queues="$(LIVE_REPORT_BULK_QUEUE_LIST)" --hostname=bulk-live@%h >> ../logs/celery_bulk_live.log 2>&1 &
	@sleep 6
	@pgrep -f "celery.*analysis-live@" >/dev/null || (echo "❌ analysis-live worker 启动失败，请检查 logs/celery_analysis_live.log" && exit 1)
	@pgrep -f "celery.*bulk-live@" >/dev/null || (echo "❌ bulk-live worker 启动失败，请检查 logs/celery_bulk_live.log" && exit 1)
	@echo "==> Running live report acceptance ..."
	@status=0; \
	(cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_live_report_acceptance.py $(LIVE_REPORT_ACCEPTANCE_ARGS)) || status=$$?; \
	$(MAKE) crawl-stop >/dev/null || true; \
	pkill -9 -f "celery.*analysis-live@" >/dev/null 2>&1 || true; \
	pkill -9 -f "celery.*bulk-live@" >/dev/null 2>&1 || true; \
	exit $$status

test-e2e-live-report-5x: ## 连跑 live report 验收，门禁要求连续5次 A_full
	@echo "==> Running live report acceptance $(LIVE_REPORT_REQUIRED_RUNS)x ..."
	@i=1; \
	while [ $$i -le $(LIVE_REPORT_REQUIRED_RUNS) ]; do \
		echo "==> [$$i/$(LIVE_REPORT_REQUIRED_RUNS)] live report acceptance"; \
		$(MAKE) test-e2e-live-report || exit $$?; \
		i=$$((i + 1)); \
	done
	@echo "✅ live report acceptance passed $(LIVE_REPORT_REQUIRED_RUNS)x"

test-e2e-topic-profile-matrix: ## 运行首页 6 卡 Full A 矩阵验收（含 report_structured 与 DB 落库校验）
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@echo "==> Running topic-profile Full A matrix acceptance ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_topic_profile_full_a_matrix.py $(TOPIC_PROFILE_MATRIX_ACCEPTANCE_ARGS)

demo-live-a-full: test-e2e-live-report ## 标准演示入口：真输入->真分析->A_full 报告
	@echo "✅ Live A_full demo flow passed"

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
	@# FIXME: scripts/check_breaking_changes.py does not exist (dead reference)
	@cd $(BACKEND_DIR) && python scripts/check_breaking_changes.py
	@echo ""
	@echo "✅ API 契约测试完成"
	@echo ""
	@echo "💡 提示: Property-based 测试（schemathesis）需要较长时间，已跳过"
	@# FIXME: scripts/test_contract.py does not exist (dead reference)
	@echo "   如需运行完整测试，请执行: cd backend && python scripts/test_contract.py"

test-admin-e2e: ## 运行当前 Admin 控制面 E2E（Playwright）
	@echo "==> Seeding admin test account ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@echo "==> Running admin dashboard E2E ..."
	@cd $(FRONTEND_DIR) && npx playwright test e2e/admin-dashboard.spec.ts $(PLAYWRIGHT_FLAGS)

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
