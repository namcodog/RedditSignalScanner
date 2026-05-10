# Test targets and diagnostics

SAFE_PYTEST := $(BACKEND_DIR)/scripts/pytest_safe.sh
PLAYWRIGHT_FORMAL_SPECS := e2e/user-journey.spec.ts e2e/report-page-simple.spec.ts e2e/product-polish-smoke.spec.ts e2e/admin-dashboard.spec.ts e2e/performance.spec.ts
PLAYWRIGHT_FLAGS ?= --project=chromium --reporter=line --workers=1
LIVE_REPORT_BULK_QUEUE_LIST ?= backfill_posts_queue_v2,backfill_queue,compensation_queue
LIVE_RUNTIME_BACKEND_PORT ?= 8016
LIVE_RUNTIME_STARTUP_TIMEOUT_SECONDS ?= 25
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
LIVE_REPORT_SEMANTIC_LOOKBACK_DAYS ?= 30
LIVE_REPORT_MIN_ACTIVE_POOL ?= 80
LIVE_REPORT_MAX_ACTIVE_POOL_CACHE_GAP_RATIO ?= 0.35
LIVE_REPORT_MAX_ACTIVE_POOL_MISSING_CATEGORIES ?= 5
LIVE_REPORT_MIN_ACTIVE_POOL_CATEGORY_MAP_COVERAGE_RATIO ?= 0.6
LIVE_REPORT_MIN_RECENT_POSTS ?= 800
LIVE_REPORT_MIN_RECENT_POSTS_LLM_LABEL_COVERAGE_RATIO ?= 0.06
LIVE_REPORT_PREFLIGHT_ARGS ?= --strict --stale-minutes $(LIVE_REPORT_BACKLOG_STALE_MINUTES) --max-stale-task-outbox-pending $(LIVE_REPORT_MAX_STALE_TASK_OUTBOX_PENDING) --max-stale-crawler-targets-not-enqueued $(LIVE_REPORT_MAX_STALE_CRAWLER_TARGETS_NOT_ENQUEUED) --semantic-lookback-days $(LIVE_REPORT_SEMANTIC_LOOKBACK_DAYS) --min-active-pool $(LIVE_REPORT_MIN_ACTIVE_POOL) --max-active-pool-cache-gap-ratio $(LIVE_REPORT_MAX_ACTIVE_POOL_CACHE_GAP_RATIO) --max-active-pool-missing-categories $(LIVE_REPORT_MAX_ACTIVE_POOL_MISSING_CATEGORIES) --min-active-pool-category-map-coverage-ratio $(LIVE_REPORT_MIN_ACTIVE_POOL_CATEGORY_MAP_COVERAGE_RATIO) --min-recent-posts $(LIVE_REPORT_MIN_RECENT_POSTS) --min-recent-posts-llm-label-coverage-ratio $(LIVE_REPORT_MIN_RECENT_POSTS_LLM_LABEL_COVERAGE_RATIO)
WARZONE_MATRIX_ARGS ?=
WARZONE_MIN_A_FULL ?= 3
WARZONE_MAX_C_SCOUTING ?= 2
WARZONE_REQUIRED_RUNS ?= 2
OPEN_QUESTION_FINAL_DESCRIPTION ?= 我做跨境电商独立站，最近订单上涨但回款和退款争议让现金流持续紧张，希望基于 Reddit 真实讨论找到一个能直接执行的产品机会。
OPEN_QUESTION_SMOKE_ARGS ?= --suite smoke --required-tier A_full --min-reddit-links 2 --max-analysis-attempts 4
OPEN_QUESTION_FINAL_ARGS ?= --suite final --required-tier A_full --min-reddit-links 2 --product-description "$(OPEN_QUESTION_FINAL_DESCRIPTION)"
HOTPOST_ACCEPTANCE_ARGS ?= --query "tiktok shop sellers" --mode trending
HOTPOST_TRENDING_QUERY ?= "tiktok shop sellers"
HOTPOST_RANT_QUERY ?= "shopify refund process"
HOTPOST_OPPORTUNITY_QUERY ?= "creator marketing tools"
FRONTEND_STABLE_CONTRACT_SPECS ?= src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx
FILE_LENGTH_GATE_ARGS ?= --scope changed --max-lines 300

.PHONY: test test-all test-backend test-frontend test-e2e test-e2e-formal test-e2e-smoke test-e2e-backend test-e2e-live-report test-e2e-live-report-5x test-e2e-live-report-preflight test-e2e-live-report-unblock-locks-dryrun test-e2e-live-report-unblock-locks-apply test-e2e-live-report-cleanup-dryrun test-e2e-live-report-cleanup-apply test-e2e-warzone-live-matrix test-e2e-warzone-live-matrix-2x test-e2e-topic-profile-matrix demo-live-a-full test-admin-e2e test-contract test-tasks-smoke test-file-length-gate
.PHONY: acceptance-offline-gate acceptance-live-smoke acceptance-live-final
.PHONY: acceptance-stable-no-playwright
.PHONY: acceptance-hotpost-smoke acceptance-hotpost-quality-smoke
.PHONY: live-runtime-start live-runtime-stop live-runtime-restart live-runtime-status
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

test-file-length-gate: ## 代码行数门禁（默认检查改动文件，每文件 <= 300 行）
	@echo "==> Running file-length gate ..."
	@$(PYTHON) $(BACKEND_DIR)/scripts/quality/check_file_length_gate.py $(FILE_LENGTH_GATE_ARGS)

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

live-runtime-start: ## 启动隔离 live runtime（backend + analysis-live + bulk-live）
	@echo "==> Starting isolated live runtime ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/manage_live_runtime.py start \
		--backend-port $(LIVE_RUNTIME_BACKEND_PORT) \
		--analysis-concurrency 2 \
		--bulk-concurrency $${BULK_WORKER_CONCURRENCY:-2} \
		--bulk-queues "$(LIVE_REPORT_BULK_QUEUE_LIST)" \
		--warmup-base-delay-seconds $(LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS) \
		--warmup-max-delay-seconds $(LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS) \
		--backfill-settle-seconds $(LIVE_REPORT_BACKFILL_SETTLE_SECONDS) \
		--backfill-max-targets $(LIVE_REPORT_BACKFILL_MAX_TARGETS) \
		--startup-timeout-seconds $(LIVE_RUNTIME_STARTUP_TIMEOUT_SECONDS)

live-runtime-stop: ## 停止隔离 live runtime
	@echo "==> Stopping isolated live runtime ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/manage_live_runtime.py stop \
		--backend-port $(LIVE_RUNTIME_BACKEND_PORT) \
		--analysis-concurrency 2 \
		--bulk-concurrency $${BULK_WORKER_CONCURRENCY:-2} \
		--bulk-queues "$(LIVE_REPORT_BULK_QUEUE_LIST)" \
		--warmup-base-delay-seconds $(LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS) \
		--warmup-max-delay-seconds $(LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS) \
		--backfill-settle-seconds $(LIVE_REPORT_BACKFILL_SETTLE_SECONDS) \
		--backfill-max-targets $(LIVE_REPORT_BACKFILL_MAX_TARGETS)

live-runtime-restart: ## 重启隔离 live runtime
	@echo "==> Restarting isolated live runtime ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/manage_live_runtime.py restart \
		--backend-port $(LIVE_RUNTIME_BACKEND_PORT) \
		--analysis-concurrency 2 \
		--bulk-concurrency $${BULK_WORKER_CONCURRENCY:-2} \
		--bulk-queues "$(LIVE_REPORT_BULK_QUEUE_LIST)" \
		--warmup-base-delay-seconds $(LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS) \
		--warmup-max-delay-seconds $(LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS) \
		--backfill-settle-seconds $(LIVE_REPORT_BACKFILL_SETTLE_SECONDS) \
		--backfill-max-targets $(LIVE_REPORT_BACKFILL_MAX_TARGETS) \
		--startup-timeout-seconds $(LIVE_RUNTIME_STARTUP_TIMEOUT_SECONDS)

live-runtime-status: ## 查看隔离 live runtime 状态
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/manage_live_runtime.py status \
		--backend-port $(LIVE_RUNTIME_BACKEND_PORT) \
		--analysis-concurrency 2 \
		--bulk-concurrency $${BULK_WORKER_CONCURRENCY:-2} \
		--bulk-queues "$(LIVE_REPORT_BULK_QUEUE_LIST)" \
		--warmup-base-delay-seconds $(LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS) \
		--warmup-max-delay-seconds $(LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS) \
		--backfill-settle-seconds $(LIVE_REPORT_BACKFILL_SETTLE_SECONDS) \
		--backfill-max-targets $(LIVE_REPORT_BACKFILL_MAX_TARGETS)

test-e2e-live-report: ## 运行实时 report 真链路验收（登录->分析->状态->报告）
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@$(MAKE) test-e2e-live-report-preflight
	@echo "==> Resetting crawler workers + pending broker backlog for deterministic acceptance ..."
	@$(MAKE) crawl-stop >/dev/null || true
	@sleep 2
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app purge -f >/dev/null || true
	@$(MAKE) live-runtime-restart
	@echo "==> Running live report acceptance ..."
	@status=0; \
	(cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_live_report_acceptance.py --base-url http://127.0.0.1:$(LIVE_RUNTIME_BACKEND_PORT) $(LIVE_REPORT_ACCEPTANCE_ARGS)) || status=$$?; \
	$(MAKE) crawl-stop >/dev/null || true; \
	$(MAKE) live-runtime-stop >/dev/null || true; \
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

test-e2e-warzone-live-matrix: ## 运行 8 领域 live matrix，并按严格门禁校验 A/C 配比
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@$(MAKE) test-e2e-live-report-preflight
	@echo "==> Resetting crawler workers + pending broker backlog for deterministic matrix run ..."
	@$(MAKE) crawl-stop >/dev/null || true
	@sleep 2
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app purge -f >/dev/null || true
	@status=0; \
	$(MAKE) live-runtime-restart || status=$$?; \
	if [ $$status -eq 0 ]; then \
		(cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_warzone_live_matrix.py --base-url http://127.0.0.1:$(LIVE_RUNTIME_BACKEND_PORT) --frontend-base-url http://127.0.0.1:$(FRONTEND_PORT) $(WARZONE_MATRIX_ARGS)) || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		latest=$$(cd $(BACKEND_DIR) && ls -1t reports/local-acceptance/warzone_live_matrix_final_*.json | head -n 1); \
		echo "==> Validating $$latest with strict gate (A>=$(WARZONE_MIN_A_FULL), C<=$(WARZONE_MAX_C_SCOUTING)) ..."; \
		(cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/acceptance/validate_warzone_live_matrix.py --input "$$latest" --min-a-full $(WARZONE_MIN_A_FULL) --max-c-scouting $(WARZONE_MAX_C_SCOUTING)) || status=$$?; \
	fi; \
	$(MAKE) crawl-stop >/dev/null || true; \
	$(MAKE) live-runtime-stop >/dev/null || true; \
	exit $$status

test-e2e-warzone-live-matrix-2x: ## 连跑 2 轮 warzone live matrix，确认稳定达标
	@echo "==> Running warzone live matrix $(WARZONE_REQUIRED_RUNS)x ..."
	@i=1; \
	while [ $$i -le $(WARZONE_REQUIRED_RUNS) ]; do \
		echo "==> [$$i/$(WARZONE_REQUIRED_RUNS)] warzone live matrix"; \
		$(MAKE) test-e2e-warzone-live-matrix || exit $$?; \
		i=$$((i + 1)); \
	done
	@echo "✅ warzone live matrix passed $(WARZONE_REQUIRED_RUNS)x"

acceptance-offline-gate: ## 开放题主链离线门禁（无 live 调度）
	@$(MAKE) test-file-length-gate
	@echo "==> Running open-question offline gate ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest \
		tests/services/report/test_analysis_payload_loader.py \
		tests/services/report/test_content_guardrails.py \
		tests/services/report/test_report_brief_builder.py \
		tests/services/report/test_report_markdown_contract.py \
		tests/services/report/test_narrative_report_workflow.py \
		tests/services/report/test_structured_report_fallback.py \
		tests/scripts/acceptance/test_validate_warzone_live_matrix.py \
		tests/scripts/acceptance/test_run_warzone_live_matrix.py \
		tests/scripts/acceptance/test_run_open_question_live_acceptance.py \
		-q

acceptance-live-smoke: ## 开放题 live smoke（3条代表题）
	@$(MAKE) acceptance-offline-gate
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@$(MAKE) test-e2e-live-report-preflight
	@echo "==> Resetting crawler workers + pending broker backlog for deterministic smoke run ..."
	@$(MAKE) crawl-stop >/dev/null || true
	@sleep 2
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app purge -f >/dev/null || true
	@status=0; \
	$(MAKE) live-runtime-restart || status=$$?; \
	if [ $$status -eq 0 ]; then \
		(cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_open_question_live_acceptance.py --base-url http://127.0.0.1:$(LIVE_RUNTIME_BACKEND_PORT) --frontend-base-url http://127.0.0.1:$(FRONTEND_PORT) $(OPEN_QUESTION_SMOKE_ARGS)) || status=$$?; \
	fi; \
	$(MAKE) crawl-stop >/dev/null || true; \
	$(MAKE) live-runtime-stop >/dev/null || true; \
	exit $$status

acceptance-live-final: ## 开放题 live final（单条最终验收）
	@$(MAKE) acceptance-offline-gate
	@echo "==> Seeding local E2E accounts ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py >/dev/null
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed/seed_test_accounts.py --reset >/dev/null
	@$(MAKE) test-e2e-live-report-preflight
	@echo "==> Resetting crawler workers + pending broker backlog for deterministic final run ..."
	@$(MAKE) crawl-stop >/dev/null || true
	@sleep 2
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app purge -f >/dev/null || true
	@status=0; \
	$(MAKE) live-runtime-restart || status=$$?; \
	if [ $$status -eq 0 ]; then \
		(cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_open_question_live_acceptance.py --base-url http://127.0.0.1:$(LIVE_RUNTIME_BACKEND_PORT) --frontend-base-url http://127.0.0.1:$(FRONTEND_PORT) $(OPEN_QUESTION_FINAL_ARGS)) || status=$$?; \
	fi; \
	$(MAKE) crawl-stop >/dev/null || true; \
	$(MAKE) live-runtime-stop >/dev/null || true; \
	exit $$status

acceptance-stable-no-playwright: ## 稳定验收主链（不依赖 Playwright）：后端门禁 + 前端契约 + live smoke + live final
	@echo "==> [1/4] Running backend offline gate ..."
	@$(MAKE) acceptance-offline-gate
	@echo "==> [2/4] Running frontend contract/integration (no browser e2e) ..."
	@cd $(FRONTEND_DIR) && npm test -- --run $(FRONTEND_STABLE_CONTRACT_SPECS)
	@echo "==> [3/4] Running live smoke ..."
	@$(MAKE) acceptance-live-smoke
	@echo "==> [4/4] Running live final ..."
	@$(MAKE) acceptance-live-final
	@echo "✅ acceptance-stable-no-playwright passed"

acceptance-hotpost-smoke: ## hotpost 正常态 smoke：检查后端/路由并跑一条 fresh 查询
	@echo "==> Running hotpost smoke acceptance ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_live_hotpost_acceptance.py --base-url http://127.0.0.1:$(BACKEND_PORT) $(HOTPOST_ACCEPTANCE_ARGS)

acceptance-hotpost-quality-smoke: ## hotpost 低成本质量 smoke：默认三模式各一题，并输出重层/缺口统计
	@echo "==> Running low-cost hotpost quality smoke ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/acceptance/run_hotpost_quality_smoke.py --base-url http://127.0.0.1:$(BACKEND_PORT) --limit $${LIMIT:-3}

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
